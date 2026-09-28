import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.session import ActivitySession
from app.utils.seed_data import seed_activities


class CompletedActivityBackNavigationTestCase(unittest.TestCase):
    """
    Tests for Bug #2 resolution:
    - Back navigation into a completed activity form (from bfcache) redirects gracefully to results with a friendly flash.
    - Out-of-bounds question indices redirect cleanly to results with a flash message rather than 400.
    - Cache-Control headers (no-store, no-cache, must-revalidate, max-age=0) are applied to child routes.
    - Normal in-progress activity gameplay and input validations are preserved.
    """

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        seed_activities()

        # Parent user
        self.parent = User(name='Parent Alice', email='alice@example.com', role='parent')
        self.parent.set_password('ParentPass123!')
        db.session.add(self.parent)
        db.session.commit()

        # Children
        self.child_en = Child(
            parent_id=self.parent.id,
            name='Leo',
            age=6,
            grade='1st Grade',
            preferred_language='English'
        )
        self.child_hi = Child(
            parent_id=self.parent.id,
            name='Aarav',
            age=7,
            grade='2nd Grade',
            preferred_language='Hindi'
        )
        db.session.add_all([self.child_en, self.child_hi])
        db.session.commit()

        self.activity = Activity.query.filter(Activity.questions.any()).first()
        self.questions = self.activity.questions.order_by(ActivityQuestion.order_num).all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login_parent(self):
        return self.client.post('/auth/login', data={
            'email': 'alice@example.com',
            'password': 'ParentPass123!'
        }, follow_redirects=False)

    def test_cache_control_headers_on_child_routes(self):
        """Verify Cache-Control, Pragma, and Expires headers prevent bfcache on child routes."""
        self._login_parent()

        routes = [
            f'/child/{self.child_en.id}/play/{self.activity.id}',
            f'/child/{self.child_en.id}/play/{self.activity.id}/results',
            f'/child/{self.child_en.id}/activities',
            f'/child/select-child'
        ]

        for route in routes:
            resp = self.client.get(route)
            self.assertEqual(resp.status_code, 200, f"Route {route} failed to return 200")
            cc = resp.headers.get('Cache-Control', '')
            self.assertIn('no-store', cc, f"Cache-Control on {route} missing no-store")
            self.assertIn('no-cache', cc, f"Cache-Control on {route} missing no-cache")
            self.assertIn('must-revalidate', cc, f"Cache-Control on {route} missing must-revalidate")
            self.assertEqual(resp.headers.get('Pragma'), 'no-cache')
            self.assertEqual(resp.headers.get('Expires'), '0')

    def test_post_answer_on_completed_session_redirects_with_friendly_flash(self):
        """
        Simulate exact Bug #2 scenario:
        1. Child plays activity to completion and reaches Results screen.
        2. Session is marked 'completed' in DB.
        3. Browser Back button is pressed (or form submitted from bfcache).
        4. Backend intercepts stale submission, does NOT return raw 400, and redirects to Results with flash message.
        """
        self._login_parent()

        # Step 1: Start activity
        self.client.get(f'/child/{self.child_en.id}/play/{self.activity.id}?q=0')

        # Answer all questions
        for idx, q in enumerate(self.questions):
            ans_resp = self.client.post(f'/child/{self.child_en.id}/play/{self.activity.id}/answer', data={
                'question_id': q.id,
                'selected_answer': q.correct_answer,
                'q_idx': idx
            })
            self.assertEqual(ans_resp.status_code, 200)

        # Reach results screen
        results_url = f'/child/{self.child_en.id}/play/{self.activity.id}/results'
        res = self.client.get(results_url)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'High Five', res.data)

        # Verify session is marked completed in DB
        act_session = ActivitySession.query.filter_by(
            child_id=self.child_en.id,
            activity_id=self.activity.id
        ).order_by(ActivitySession.id.desc()).first()
        self.assertIsNotNone(act_session)
        self.assertEqual(act_session.status, ActivitySession.STATUS_COMPLETED)

        # Step 2: Simulate Back button and resubmission of completed question form
        first_q = self.questions[0]
        stale_resp = self.client.post(
            f'/child/{self.child_en.id}/play/{self.activity.id}/answer',
            data={
                'question_id': first_q.id,
                'selected_answer': first_q.correct_answer,
                'q_idx': 0,
                'session_id': act_session.id
            },
            follow_redirects=False
        )

        # Must NOT return 400 or crash; must redirect cleanly to results
        self.assertEqual(stale_resp.status_code, 302)
        self.assertIn(results_url, stale_resp.headers['Location'])

        # Following redirect shows friendly flash message
        follow_resp = self.client.get(stale_resp.headers['Location'])
        self.assertEqual(follow_resp.status_code, 200)
        self.assertIn('This activity is already finished! Here are your results.', follow_resp.data.decode('utf-8'))

    def test_post_answer_out_of_bounds_question_index_redirects_with_flash(self):
        """When submitted question index is out of bounds (q_idx >= len(questions)), redirect to results with flash."""
        self._login_parent()

        # Submit answer with out-of-bounds q_idx = 99
        first_q = self.questions[0]
        resp = self.client.post(
            f'/child/{self.child_en.id}/play/{self.activity.id}/answer',
            data={
                'question_id': first_q.id,
                'selected_answer': first_q.correct_answer,
                'q_idx': 99
            },
            follow_redirects=False
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn(f'/child/{self.child_en.id}/play/{self.activity.id}/results', resp.headers['Location'])

        follow_resp = self.client.get(resp.headers['Location'])
        self.assertEqual(follow_resp.status_code, 200)
        self.assertIn('This activity is already finished! Here are your results.', follow_resp.data.decode('utf-8'))

    def test_post_skip_on_completed_session_redirects_with_flash(self):
        """Clicking skip on a completed session redirects gracefully with flash."""
        self._login_parent()

        # Mark session as completed
        act_session = ActivitySession(
            child_id=self.child_en.id,
            activity_id=self.activity.id,
            status=ActivitySession.STATUS_COMPLETED,
            attempts=len(self.questions),
            correct_answers=len(self.questions)
        )
        db.session.add(act_session)
        db.session.commit()

        first_q = self.questions[0]
        resp = self.client.post(
            f'/child/{self.child_en.id}/play/{self.activity.id}/skip',
            data={
                'question_id': first_q.id,
                'q_idx': 0,
                'session_id': act_session.id
            },
            follow_redirects=False
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn(f'/child/{self.child_en.id}/play/{self.activity.id}/results', resp.headers['Location'])

    def test_get_player_with_stale_question_index_on_completed_activity(self):
        """If child navigates back via GET to ?q=1 on a completed activity, redirect to results."""
        self._login_parent()

        act_session = ActivitySession(
            child_id=self.child_en.id,
            activity_id=self.activity.id,
            status=ActivitySession.STATUS_COMPLETED,
            attempts=len(self.questions),
            correct_answers=len(self.questions)
        )
        db.session.add(act_session)
        db.session.commit()

        resp = self.client.get(
            f'/child/{self.child_en.id}/play/{self.activity.id}?q=1',
            follow_redirects=False
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f'/child/{self.child_en.id}/play/{self.activity.id}/results', resp.headers['Location'])

    def test_results_revisit_preserves_score(self):
        """Revisiting results page repeatedly displays the child's recorded score, not 0."""
        self._login_parent()

        act_session = ActivitySession(
            child_id=self.child_en.id,
            activity_id=self.activity.id,
            status=ActivitySession.STATUS_COMPLETED,
            attempts=len(self.questions),
            correct_answers=len(self.questions)
        )
        db.session.add(act_session)
        db.session.commit()

        resp = self.client.get(f'/child/{self.child_en.id}/play/{self.activity.id}/results')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Superstar!', resp.data)

        # Second visit
        resp2 = self.client.get(f'/child/{self.child_en.id}/play/{self.activity.id}/results')
        self.assertEqual(resp2.status_code, 200)
        self.assertIn(b'Superstar!', resp2.data)

    def test_hindi_child_flash_message_translated(self):
        """When child's language is Hindi, the completion redirect flash message is in Hindi."""
        self._login_parent()

        act_session = ActivitySession(
            child_id=self.child_hi.id,
            activity_id=self.activity.id,
            status=ActivitySession.STATUS_COMPLETED,
            attempts=len(self.questions),
            correct_answers=len(self.questions)
        )
        db.session.add(act_session)
        db.session.commit()

        first_q = self.questions[0]
        resp = self.client.post(
            f'/child/{self.child_hi.id}/play/{self.activity.id}/answer',
            data={
                'question_id': first_q.id,
                'selected_answer': first_q.correct_answer,
                'q_idx': 0,
                'session_id': act_session.id
            },
            follow_redirects=True
        )
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('यह गतिविधि पहले ही पूरी हो चुकी है! यहाँ आपके परिणाम हैं।', html)

    def test_valid_in_progress_answer_still_functions(self):
        """Normal gameplay continues to work with immediate feedback."""
        self._login_parent()

        self.client.get(f'/child/{self.child_en.id}/play/{self.activity.id}?q=0')
        first_q = self.questions[0]
        resp = self.client.post(
            f'/child/{self.child_en.id}/play/{self.activity.id}/answer',
            data={
                'question_id': first_q.id,
                'selected_answer': first_q.correct_answer,
                'q_idx': 0
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Great job!', resp.data)

    def test_empty_answer_aborts_400_for_active_session(self):
        """Input validation strictly returns 400 for bad input in an active session."""
        self._login_parent()

        self.client.get(f'/child/{self.child_en.id}/play/{self.activity.id}?q=0')
        first_q = self.questions[0]
        resp = self.client.post(
            f'/child/{self.child_en.id}/play/{self.activity.id}/answer',
            data={
                'question_id': first_q.id,
                'selected_answer': '',
                'q_idx': 0
            }
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
