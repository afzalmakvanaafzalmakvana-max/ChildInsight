import unittest
from datetime import datetime, timezone
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.session import ActivitySession, InteractionEvent
from app.utils.seed_data import seed_activities
from app.services import event_tracker


class Phase4DataCollectionTestCase(unittest.TestCase):
    """Automated test suite verifying Phase 4 Data Collection, validation rules, and event tracking."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed test users
        self.parent_a = User(name='Parent A', email='parent_a@example.com', role='parent')
        self.parent_a.set_password('Pass123!')

        self.parent_b = User(name='Parent B', email='parent_b@example.com', role='parent')
        self.parent_b.set_password('Pass123!')

        db.session.add_all([self.parent_a, self.parent_b])
        db.session.commit()

        # Children
        self.child_a = Child(parent_id=self.parent_a.id, name='Timmy', age=6, grade='1st Grade', preferred_language='English')
        self.child_b = Child(parent_id=self.parent_b.id, name='Sara', age=7, grade='2nd Grade', preferred_language='English')

        db.session.add_all([self.child_a, self.child_b])
        db.session.commit()

        # Seed activities
        seed_activities()
        self.activity = Activity.query.first()
        self.questions = self.activity.questions.order_by(ActivityQuestion.order_num).all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password='Pass123!'):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    # --- 1. Validation Rules (rules.md §4) ---

    def test_validation_accuracy_range(self):
        """Accuracy must be within 0.0 and 100.0 inclusive."""
        sess = ActivitySession(
            child_id=self.child_a.id,
            activity_id=self.activity.id,
            attempts=1,
            correct_answers=1,
            accuracy=100.0
        )
        db.session.add(sess)
        db.session.commit()
        self.assertEqual(sess.accuracy, 100.0)

        # Accuracy < 0 must raise ValueError
        with self.assertRaises(ValueError):
            sess.accuracy = -5.0

        # Accuracy > 100 must raise ValueError
        with self.assertRaises(ValueError):
            sess.accuracy = 105.0

    def test_validation_attempts_gte_correct_answers(self):
        """Attempts must always be greater than or equal to correct_answers."""
        # Initial valid session
        sess = ActivitySession(
            child_id=self.child_a.id,
            activity_id=self.activity.id,
            attempts=3,
            correct_answers=2,
            accuracy=66.67
        )
        db.session.add(sess)
        db.session.commit()

        # Setting attempts lower than correct_answers must raise ValueError
        with self.assertRaises(ValueError):
            sess.attempts = 1

        # Setting correct_answers higher than attempts must raise ValueError
        with self.assertRaises(ValueError):
            sess.correct_answers = 5

        # Attempts cannot be negative
        with self.assertRaises(ValueError):
            sess.attempts = -1

        # Correct answers cannot be negative
        with self.assertRaises(ValueError):
            sess.correct_answers = -1

    def test_validation_duration_non_negative(self):
        """Duration seconds cannot be negative."""
        sess = ActivitySession(
            child_id=self.child_a.id,
            activity_id=self.activity.id,
            duration_seconds=120
        )
        db.session.add(sess)
        db.session.commit()
        self.assertEqual(sess.duration_seconds, 120)

        with self.assertRaises(ValueError):
            sess.duration_seconds = -10

    def test_validation_status_values(self):
        """Session status must be in ('in_progress', 'completed', 'abandoned')."""
        sess = ActivitySession(child_id=self.child_a.id, activity_id=self.activity.id)
        self.assertEqual(sess.status, 'in_progress')

        sess.status = 'completed'
        self.assertEqual(sess.status, 'completed')

        sess.status = 'abandoned'
        self.assertEqual(sess.status, 'abandoned')

        with self.assertRaises(ValueError):
            sess.status = 'invalid_state'

    def test_recalculate_accuracy_helper(self):
        """Verify accuracy recalculation logic and edge cases."""
        sess = ActivitySession(child_id=self.child_a.id, activity_id=self.activity.id)
        self.assertEqual(sess.recalculate_accuracy(), 0.0)

        sess.attempts = 4
        sess.correct_answers = 3
        self.assertEqual(sess.recalculate_accuracy(), 75.0)

        sess.attempts = 3
        sess.correct_answers = 1
        self.assertEqual(sess.recalculate_accuracy(), 33.33)

    # --- 2. Interaction Events Linkage to Session & Child ---

    def test_interaction_events_linkage_to_session_and_child(self):
        """Verify interaction events correctly link to both the session and child."""
        act_session = event_tracker.start_session(child_id=self.child_a.id, activity_id=self.activity.id)
        q1 = self.questions[0]

        # Log various events
        ev_view = event_tracker.log_question_viewed(act_session.id, self.child_a.id, q1.id, q_idx=0)
        ev_hint = event_tracker.log_hint_used(act_session.id, self.child_a.id, q1.id)
        _, ev_ans = event_tracker.record_answer(act_session.id, self.child_a.id, q1.id, q1.correct_answer, True)
        ev_comp = event_tracker.complete_session(act_session.id, self.child_a.id)

        # Check all events in database
        events = InteractionEvent.query.filter_by(session_id=act_session.id).all()
        self.assertGreaterEqual(len(events), 5)  # started, question_viewed, hint_used, answer_selected, correct, completed

        for ev in events:
            # Must link to the exact session
            self.assertEqual(ev.session_id, act_session.id)
            self.assertEqual(ev.session.id, act_session.id)
            # Must link to the exact child
            self.assertEqual(ev.child_id, self.child_a.id)
            self.assertEqual(ev.child.id, self.child_a.id)
            self.assertIsNotNone(ev.timestamp)
            self.assertIn(ev.event_type, InteractionEvent.ALLOWED_EVENT_TYPES)

        # Child relationship query
        child_events = self.child_a.interaction_events.all()
        self.assertEqual(len(child_events), len(events))

        # Child B must have zero events
        child_b_events = self.child_b.interaction_events.all()
        self.assertEqual(len(child_b_events), 0)

    def test_interaction_event_invalid_type(self):
        """Invalid event types must be rejected by model validation."""
        act_session = event_tracker.start_session(child_id=self.child_a.id, activity_id=self.activity.id)
        with self.assertRaises(ValueError):
            ev = InteractionEvent(
                session_id=act_session.id,
                child_id=self.child_a.id,
                event_type='totally_fake_event'
            )

    def test_cascade_delete_session_removes_events(self):
        """Deleting a session cascades and cleans up all its events."""
        act_session = event_tracker.start_session(child_id=self.child_a.id, activity_id=self.activity.id)
        event_tracker.log_question_viewed(act_session.id, self.child_a.id, self.questions[0].id)
        event_id = act_session.events.first().id

        db.session.delete(act_session)
        db.session.commit()

        # Event should be deleted via cascade
        self.assertIsNone(db.session.get(InteractionEvent, event_id))

    # --- 3. Activity Player Real-Time Tracking Flow ---

    def test_player_start_creates_session_and_events(self):
        """Opening question 1 creates an in-progress session and logs started & viewed events."""
        self._login('parent_a@example.com')
        resp = self.client.get(f'/child/{self.child_a.id}/play/{self.activity.id}')
        self.assertEqual(resp.status_code, 200)

        # Verify session was created
        act_session = ActivitySession.query.filter_by(
            child_id=self.child_a.id,
            activity_id=self.activity.id,
            status=ActivitySession.STATUS_IN_PROGRESS
        ).first()
        self.assertIsNotNone(act_session)

        # Check events
        event_types = [e.event_type for e in act_session.events]
        self.assertIn('started', event_types)
        self.assertIn('question_viewed', event_types)

    def test_player_answer_correct_and_incorrect_flow(self):
        """Answering questions logs answer_selected, correct/incorrect, and updates accuracy."""
        self._login('parent_a@example.com')

        # Start player
        self.client.get(f'/child/{self.child_a.id}/play/{self.activity.id}')
        act_session = ActivitySession.query.filter_by(
            child_id=self.child_a.id,
            activity_id=self.activity.id,
            status=ActivitySession.STATUS_IN_PROGRESS
        ).first()

        q1 = self.questions[0]
        q2 = self.questions[1]

        # 1. Answer Q1 correctly
        ans1_resp = self.client.post(
            f'/child/{self.child_a.id}/play/{self.activity.id}/answer',
            data={'question_id': q1.id, 'selected_answer': q1.correct_answer, 'q_idx': '0'}
        )
        self.assertEqual(ans1_resp.status_code, 200)

        db.session.refresh(act_session)
        self.assertEqual(act_session.attempts, 1)
        self.assertEqual(act_session.correct_answers, 1)
        self.assertEqual(act_session.accuracy, 100.0)

        # 2. Answer Q2 incorrectly
        wrong_choice = [opt for opt in q2.options if opt != q2.correct_answer][0]
        ans2_resp = self.client.post(
            f'/child/{self.child_a.id}/play/{self.activity.id}/answer',
            data={'question_id': q2.id, 'selected_answer': wrong_choice, 'q_idx': '1'}
        )
        self.assertEqual(ans2_resp.status_code, 200)

        db.session.refresh(act_session)
        self.assertEqual(act_session.attempts, 2)
        self.assertEqual(act_session.correct_answers, 1)
        self.assertEqual(act_session.accuracy, 50.0)

        event_types = [e.event_type for e in act_session.events]
        self.assertIn('answer_selected', event_types)
        self.assertIn('correct', event_types)
        self.assertIn('incorrect', event_types)

    def test_player_hint_used_event(self):
        """Requesting a hint logs a hint_used event for the question."""
        self._login('parent_a@example.com')
        self.client.get(f'/child/{self.child_a.id}/play/{self.activity.id}')
        act_session = ActivitySession.query.filter_by(
            child_id=self.child_a.id,
            activity_id=self.activity.id,
            status=ActivitySession.STATUS_IN_PROGRESS
        ).first()

        q1 = self.questions[0]
        hint_resp = self.client.post(
            f'/child/{self.child_a.id}/play/{self.activity.id}/hint',
            data={'question_id': q1.id, 'q_idx': '0'},
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(hint_resp.status_code, 200)

        db.session.refresh(act_session)
        hint_events = act_session.events.filter_by(event_type='hint_used').all()
        self.assertEqual(len(hint_events), 1)
        self.assertEqual(hint_events[0].question_id, q1.id)

    def test_player_skip_question_event(self):
        """Skipping a question logs skipped event and counts as an attempt."""
        self._login('parent_a@example.com')
        self.client.get(f'/child/{self.child_a.id}/play/{self.activity.id}')
        act_session = ActivitySession.query.filter_by(
            child_id=self.child_a.id,
            activity_id=self.activity.id,
            status=ActivitySession.STATUS_IN_PROGRESS
        ).first()

        q1 = self.questions[0]
        skip_resp = self.client.post(
            f'/child/{self.child_a.id}/play/{self.activity.id}/skip',
            data={'question_id': q1.id, 'q_idx': '0'},
            follow_redirects=True
        )
        self.assertEqual(skip_resp.status_code, 200)

        db.session.refresh(act_session)
        self.assertEqual(act_session.attempts, 1)
        self.assertEqual(act_session.correct_answers, 0)
        self.assertEqual(act_session.accuracy, 0.0)

        skip_events = act_session.events.filter_by(event_type='skipped').all()
        self.assertEqual(len(skip_events), 1)
        self.assertEqual(skip_events[0].question_id, q1.id)

    def test_player_completion_finalizes_session(self):
        """Reaching results screen marks session completed and records duration."""
        self._login('parent_a@example.com')
        self.client.get(f'/child/{self.child_a.id}/play/{self.activity.id}')
        act_session = ActivitySession.query.filter_by(
            child_id=self.child_a.id,
            activity_id=self.activity.id,
            status=ActivitySession.STATUS_IN_PROGRESS
        ).first()

        results_resp = self.client.get(f'/child/{self.child_a.id}/play/{self.activity.id}/results')
        self.assertEqual(results_resp.status_code, 200)

        db.session.refresh(act_session)
        self.assertEqual(act_session.status, ActivitySession.STATUS_COMPLETED)
        self.assertIsNotNone(act_session.end_time)
        self.assertGreaterEqual(act_session.duration_seconds, 0)

        comp_event = act_session.events.filter_by(event_type='completed').first()
        self.assertIsNotNone(comp_event)

    def test_player_abandon_event(self):
        """Exiting activity marks session abandoned and records duration."""
        self._login('parent_a@example.com')
        self.client.get(f'/child/{self.child_a.id}/play/{self.activity.id}')
        act_session = ActivitySession.query.filter_by(
            child_id=self.child_a.id,
            activity_id=self.activity.id,
            status=ActivitySession.STATUS_IN_PROGRESS
        ).first()

        abandon_resp = self.client.get(f'/child/{self.child_a.id}/play/{self.activity.id}/abandon', follow_redirects=True)
        self.assertEqual(abandon_resp.status_code, 200)

        db.session.refresh(act_session)
        self.assertEqual(act_session.status, ActivitySession.STATUS_ABANDONED)
        self.assertIsNotNone(act_session.end_time)

        ab_event = act_session.events.filter_by(event_type='abandoned').first()
        self.assertIsNotNone(ab_event)

    # --- 4. Access Control & API Endpoints ---

    def test_parent_cannot_access_another_parents_session_api(self):
        """Parent B cannot view Parent A's child sessions via API."""
        act_session = event_tracker.start_session(child_id=self.child_a.id, activity_id=self.activity.id)

        self._login('parent_b@example.com')
        resp = self.client.get(f'/api/sessions/{act_session.id}')
        self.assertEqual(resp.status_code, 403)

    def test_api_session_creation_and_retrieval(self):
        """Parent A creates session and fetches its details via REST API."""
        self._login('parent_a@example.com')

        # 1. Create session via POST /api/sessions
        create_resp = self.client.post(
            '/api/sessions',
            json={'child_id': self.child_a.id, 'activity_id': self.activity.id}
        )
        self.assertEqual(create_resp.status_code, 201)
        sess_data = create_resp.get_json()['session']
        sess_id = sess_data['id']

        # 2. Retrieve session via GET /api/sessions/<id>
        get_resp = self.client.get(f'/api/sessions/{sess_id}')
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.get_json()['session']
        self.assertEqual(data['id'], sess_id)
        self.assertEqual(data['child_id'], self.child_a.id)
        self.assertIn('events', data)
        self.assertGreaterEqual(len(data['events']), 1)
        self.assertEqual(data['events'][0]['event_type'], 'started')


if __name__ == '__main__':
    unittest.main()
