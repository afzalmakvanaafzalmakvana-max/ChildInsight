import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import os
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.session import ActivitySession
from app.models.content_suggestion import ContentSuggestion
from app.agent import content_suggestion_agent, scheduler
from app.services import analytics_service


class ContentSuggestionsTestCase(unittest.TestCase):
    """Automated tests for Adaptive Content Suggestion Agent and admin review workflow."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create platform roles
        self.admin = User(name='Admin User', email='admin@example.com', role='admin', is_active=True)
        self.admin.set_password('AdminPass123!')

        self.parent = User(name='Parent User', email='parent@example.com', role='parent', is_active=True)
        self.parent.set_password('ParentPass123!')

        self.teacher = User(name='Teacher User', email='teacher@example.com', role='teacher', is_active=True)
        self.teacher.set_password('TeacherPass123!')

        db.session.add_all([self.admin, self.parent, self.teacher])
        db.session.commit()

        # Create basic categories
        self.cat_logic = Category(name='Logic', slug='logic', icon='🧩', description='Logic puzzles')
        self.cat_visual = Category(name='Visual Learning', slug='visual', icon='🎨', description='Visual puzzles')
        db.session.add_all([self.cat_logic, self.cat_visual])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_as(self, user):
        self.client.get('/auth/logout')
        return self.client.post('/auth/login', data={
            'email': user.email,
            'password': 'AdminPass123!' if user.role == 'admin' else ('ParentPass123!' if user.role == 'parent' else 'TeacherPass123!')
        }, follow_redirects=True)

    def test_agent_detects_age_coverage_gap(self):
        """Verify agent detects when an active age band has < 2 activities in a category."""
        # Create a 13-year-old child (age band 12-14)
        teen = Child(name='Zane Teen', age=13, parent_id=self.parent.id)
        db.session.add(teen)
        # Visual category has 0 activities for ages 12-14
        db.session.commit()

        suggestions = content_suggestion_agent.generate_suggestions(persist=True)
        gap_types = [s.suggestion_type for s in suggestions]
        self.assertIn(ContentSuggestion.TYPE_AGE_COVERAGE_GAP, gap_types)

        visual_gap = next(s for s in suggestions if s.suggestion_type == ContentSuggestion.TYPE_AGE_COVERAGE_GAP and s.category_id == self.cat_visual.id)
        self.assertEqual(visual_gap.age_band, '12-14')
        self.assertIn('12-14', visual_gap.reason)
        self.assertIn('Visual Learning', visual_gap.reason)

    def test_agent_detects_progression_gap(self):
        """Verify agent detects when learners cluster at a difficulty with high accuracy but next tier is empty."""
        child = Child(name='Mia Smart', age=7, parent_id=self.parent.id) # Age band 6-9
        db.session.add(child)
        db.session.commit()

        # Create an Easy activity in Logic for age band 6-9
        act_easy = Activity(
            category_id=self.cat_logic.id,
            title='Easy Logic Clues',
            difficulty='Easy',
            min_age=6,
            max_age=9,
            is_active=True
        )
        db.session.add(act_easy)
        db.session.commit()

        # Simulate completed high-accuracy sessions at Easy level
        s1 = ActivitySession(
            child_id=child.id,
            activity_id=act_easy.id,
            accuracy=90.0,
            status=ActivitySession.STATUS_COMPLETED,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc)
        )
        s2 = ActivitySession(
            child_id=child.id,
            activity_id=act_easy.id,
            accuracy=85.0,
            status=ActivitySession.STATUS_COMPLETED,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc)
        )
        db.session.add_all([s1, s2])
        db.session.commit()

        # Medium tier for Logic in age band 6-9 has 0 activities!
        suggestions = content_suggestion_agent.generate_suggestions(persist=True)
        prog_gaps = [s for s in suggestions if s.suggestion_type == ContentSuggestion.TYPE_PROGRESSION_GAP]
        self.assertTrue(len(prog_gaps) > 0)

        prog_sugg = next(s for s in prog_gaps if s.category_id == self.cat_logic.id)
        self.assertEqual(prog_sugg.age_band, '6-9')
        self.assertEqual(prog_sugg.target_difficulty, 'Medium')
        self.assertIn('Medium', prog_sugg.reason)
        self.assertIn('Logic', prog_sugg.reason)

    def test_agent_detects_content_imbalance(self):
        """Verify agent flags categories with very low activity counts."""
        # Visual category has 0 activities (< 5)
        suggestions = content_suggestion_agent.generate_suggestions(persist=True)
        imbalance_suggs = [s for s in suggestions if s.suggestion_type == ContentSuggestion.TYPE_CONTENT_IMBALANCE]
        self.assertTrue(len(imbalance_suggs) > 0)
        self.assertTrue(any(s.category_id == self.cat_visual.id for s in imbalance_suggs))

    def test_agent_idempotency_does_not_duplicate_pending(self):
        """Verify running the agent repeatedly does not duplicate pending suggestions."""
        teen = Child(name='Zane Teen', age=13, parent_id=self.parent.id)
        db.session.add(teen)
        db.session.commit()

        suggs1 = content_suggestion_agent.generate_suggestions(persist=True)
        count1 = ContentSuggestion.query.count()

        suggs2 = content_suggestion_agent.generate_suggestions(persist=True)
        count2 = ContentSuggestion.query.count()

        self.assertEqual(count1, count2)

    def test_agent_deduplicates_pending_suggestions(self):
        """Verify that multiple heuristics matching the same category/overlapping age band produce at most one consolidated pending suggestion."""
        # Create 3 additional categories so platform has 5 categories (enabling domain expansion heuristic)
        cat_math = Category(name='Math', slug='math', icon='🔢')
        cat_memory = Category(name='Memory', slug='memory', icon='🧠')
        cat_science = Category(name='Science & Nature', slug='science-nature', icon='🔬')
        db.session.add_all([cat_math, cat_memory, cat_science])
        db.session.commit()

        # Add children across different age bands
        child_4_6 = Child(name='Kid PreK', age=5, parent_id=self.parent.id)
        child_6_9 = Child(name='Kid Elem', age=7, parent_id=self.parent.id)
        child_12_14 = Child(name='Kid Teen', age=13, parent_id=self.parent.id)
        db.session.add_all([child_4_6, child_6_9, child_12_14])
        db.session.commit()

        # Add an activity in Logic and 12 completed sessions to satisfy platform session threshold
        act_logic = Activity(
            category_id=self.cat_logic.id,
            title='Base Logic Task',
            difficulty='Easy',
            min_age=4,
            max_age=14,
            is_active=True
        )
        db.session.add(act_logic)
        db.session.commit()

        for _ in range(12):
            s = ActivitySession(
                child_id=child_6_9.id,
                activity_id=act_logic.id,
                accuracy=80.0,
                status=ActivitySession.STATUS_COMPLETED,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc)
            )
            db.session.add(s)
        db.session.commit()

        # Run suggestion agent: multiple heuristics detect gaps for Science & Nature
        # (age coverage gap for 4-6, 6-9, 12-14, content imbalance for All, and domain expansion for Science & Nature)
        suggs_run1 = content_suggestion_agent.generate_suggestions(persist=True)

        science_pending = ContentSuggestion.query.filter(
            (ContentSuggestion.category_id == cat_science.id) |
            (ContentSuggestion.suggested_title.like('%Science & Nature%')),
            ContentSuggestion.status == ContentSuggestion.STATUS_PENDING
        ).all()

        # Must have at most ONE consolidated pending suggestion for Science & Nature
        self.assertEqual(len(science_pending), 1, "Expected exactly one consolidated pending suggestion for Science & Nature!")
        consolidated = science_pending[0]
        self.assertEqual(consolidated.age_band, 'All (4-14)')
        self.assertEqual(consolidated.persistence_count, 1)

        # Running the suggestion agent a second time should maintain at most one pending suggestion and increment persistence
        suggs_run2 = content_suggestion_agent.generate_suggestions(persist=True)
        science_pending_run2 = ContentSuggestion.query.filter(
            (ContentSuggestion.category_id == cat_science.id) |
            (ContentSuggestion.suggested_title.like('%Science & Nature%')),
            ContentSuggestion.status == ContentSuggestion.STATUS_PENDING
        ).all()
        self.assertEqual(len(science_pending_run2), 1, "Must maintain at most one pending suggestion across multiple runs!")
        self.assertEqual(science_pending_run2[0].persistence_count, 2)

    def test_dismiss_content_suggestion(self):
        """Verify dismissing a suggestion sets status to dismissed."""
        sugg = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_AGE_COVERAGE_GAP,
            category_id=self.cat_logic.id,
            age_band='9-12',
            target_difficulty='Medium',
            reason='Test gap reason',
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add(sugg)
        db.session.commit()

        self.login_as(self.admin)
        res = self.client.post(f'/admin/content-suggestions/{sugg.id}/dismiss', follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        reloaded = db.session.get(ContentSuggestion, sugg.id)
        self.assertEqual(reloaded.status, ContentSuggestion.STATUS_DISMISSED)
        self.assertTrue(reloaded.is_dismissed)

    def test_create_activity_prefills_form_and_approves_suggestion(self):
        """Verify 'Create Activity' route pre-fills values from query params and approves suggestion upon creation."""
        sugg = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_PROGRESSION_GAP,
            category_id=self.cat_logic.id,
            age_band='6-9',
            target_difficulty='Medium',
            suggested_title='Logic Maze Quest',
            reason='Progression bottleneck detected',
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add(sugg)
        db.session.commit()

        self.login_as(self.admin)

        # GET request with query params
        res = self.client.get(
            f'/admin/activities/new?category_id={sugg.category_id}&difficulty={sugg.target_difficulty}&age_band={sugg.age_band}&title={sugg.suggested_title}&suggestion_id={sugg.id}'
        )
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Verify pre-filled values in HTML
        self.assertIn('Logic Maze Quest', html)
        self.assertIn('value="6"', html)  # min_age
        self.assertIn('value="9"', html)  # max_age

        # POST submission to create activity and fulfill suggestion
        post_res = self.client.post(
            f'/admin/activities/new?suggestion_id={sugg.id}',
            data={
                'title': 'Logic Maze Quest',
                'description': 'Solve the stepping stone logic maze',
                'category_id': self.cat_logic.id,
                'difficulty': 'Medium',
                'estimated_duration': 6,
                'min_age': 6,
                'max_age': 9,
                'is_active': 'y'
            },
            follow_redirects=True
        )
        self.assertEqual(post_res.status_code, 200)

        # Confirm activity created
        act = Activity.query.filter_by(title='Logic Maze Quest').first()
        self.assertIsNotNone(act)
        self.assertEqual(act.category_id, self.cat_logic.id)

        # Confirm suggestion marked approved
        reloaded = db.session.get(ContentSuggestion, sugg.id)
        self.assertEqual(reloaded.status, ContentSuggestion.STATUS_APPROVED)
        self.assertTrue(reloaded.is_approved)

    def test_create_category_prefills_form_and_approves_suggestion(self):
        """Verify 'Create Category' route pre-fills suggested name and approves suggestion upon creation."""
        sugg = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_NEW_CATEGORY,
            category_id=None,
            suggested_title='Science & Nature',
            reason='Domain expansion opportunity',
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add(sugg)
        db.session.commit()

        self.login_as(self.admin)

        # GET request with query params
        res = self.client.get('/admin/categories/new', query_string={'name': sugg.suggested_title, 'suggestion_id': sugg.id})
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('Science &amp; Nature', html)

        # POST submission to create category
        post_res = self.client.post(
            f'/admin/categories/new?suggestion_id={sugg.id}',
            data={
                'name': 'Science & Nature',
                'description': 'Interactive natural science investigations',
                'icon': '🔬'
            },
            follow_redirects=True
        )
        self.assertEqual(post_res.status_code, 200)

        # Confirm category created
        new_cat = Category.query.filter_by(name='Science & Nature').first()
        self.assertIsNotNone(new_cat)

        # Confirm suggestion marked approved
        reloaded = db.session.get(ContentSuggestion, sugg.id)
        self.assertEqual(reloaded.status, ContentSuggestion.STATUS_APPROVED)

    def test_non_admin_cannot_access_content_suggestions(self):
        """Verify unauthenticated, parent, and teacher users cannot access /admin/content-suggestions."""
        # 1. Anonymous user
        anon_res = self.client.get('/admin/content-suggestions')
        self.assertEqual(anon_res.status_code, 302)

        # 2. Parent user
        self.login_as(self.parent)
        parent_res = self.client.get('/admin/content-suggestions')
        self.assertEqual(parent_res.status_code, 403)

        # 3. Teacher user
        self.login_as(self.teacher)
        teacher_res = self.client.get('/admin/content-suggestions')
        self.assertEqual(teacher_res.status_code, 403)

        # 4. Admin user succeeds
        self.login_as(self.admin)
        admin_res = self.client.get('/admin/content-suggestions')
        self.assertEqual(admin_res.status_code, 200)
        self.assertIn('Adaptive Content Suggestions', admin_res.get_data(as_text=True))

    def test_scheduler_runs_suggestion_agent_step(self):
        """Verify scheduler maintenance pipeline executes Step 5 Adaptive Content Suggestions."""
        result = scheduler.run_maintenance_pipeline(triggered_by='test')
        self.assertIn(result['status'], ('success', 'partial_failure'))

        step_names = [s['name'] for s in result['steps']]
        self.assertIn('Adaptive Content Suggestions', step_names)
        step_5 = next(s for s in result['steps'] if s['name'] == 'Adaptive Content Suggestions')
        self.assertEqual(step_5['status'], 'success')

    def test_reason_string_contains_real_computed_numbers(self):
        """Verify suggestion reasons include real computed numbers from sample data rather than generic text."""
        child1 = Child(name='Ella Math', age=7, parent_id=self.parent.id)
        child2 = Child(name='Noah Math', age=8, parent_id=self.parent.id)
        db.session.add_all([child1, child2])
        db.session.commit()

        act_easy = Activity(
            category_id=self.cat_logic.id,
            title='Logic Clue Hunt',
            difficulty='Easy',
            min_age=6,
            max_age=9,
            is_active=True
        )
        db.session.add(act_easy)
        db.session.commit()

        # 4 completed sessions: (85 + 95 + 80 + 90) / 4 = 87.5% -> 88%
        for kid, accs in [(child1, [85.0, 95.0]), (child2, [80.0, 90.0])]:
            for acc in accs:
                s = ActivitySession(
                    child_id=kid.id,
                    activity_id=act_easy.id,
                    accuracy=acc,
                    status=ActivitySession.STATUS_COMPLETED,
                    start_time=datetime.now(timezone.utc),
                    end_time=datetime.now(timezone.utc)
                )
                db.session.add(s)
        db.session.commit()

        suggestions = content_suggestion_agent.generate_suggestions(persist=True)
        prog_sugg = next(s for s in suggestions if s.suggestion_type == ContentSuggestion.TYPE_PROGRESSION_GAP and s.category_id == self.cat_logic.id)

        # Assert exact computed numbers in reason string
        self.assertIn("2 children aged 6-9", prog_sugg.reason)
        self.assertIn("88% accuracy", prog_sugg.reason)
        self.assertIn("0 Medium activity(ies)", prog_sugg.reason)
        self.assertIn("persisted for 1 scheduler run(s)", prog_sugg.reason)
        self.assertGreater(prog_sugg.priority_score, 0.0)

    def test_gap_persistence_tracking_across_multiple_runs(self):
        """Verify recurring gaps increment persistence_count and update reason across multiple scheduler runs without duplicating."""
        # 3 children aged 13 in Visual Learning with 0 activities
        for i in range(3):
            c = Child(name=f'Teen {i}', age=13, parent_id=self.parent.id)
            db.session.add(c)
        db.session.commit()

        # Run 1
        suggs_1 = content_suggestion_agent.generate_suggestions(persist=True)
        gap = next(s for s in suggs_1 if s.suggestion_type == ContentSuggestion.TYPE_AGE_COVERAGE_GAP and s.category_id == self.cat_visual.id)
        gap_id = gap.id
        self.assertEqual(gap.persistence_count, 1)
        self.assertIn("persisted for 1 scheduler run(s)", gap.reason)
        # Priority: (3 children * 2.0) + (1 run * 5.0) = 11.0
        self.assertEqual(gap.priority_score, 11.0)
        pending_count_1 = ContentSuggestion.query.filter_by(status=ContentSuggestion.STATUS_PENDING).count()

        # Run 2
        suggs_2 = content_suggestion_agent.generate_suggestions(persist=True)
        reloaded_1 = db.session.get(ContentSuggestion, gap_id)
        self.assertEqual(reloaded_1.persistence_count, 2)
        self.assertIn("persisted for 2 scheduler run(s)", reloaded_1.reason)
        # Priority: (3 children * 2.0) + (2 runs * 5.0) = 16.0
        self.assertEqual(reloaded_1.priority_score, 16.0)
        pending_count_2 = ContentSuggestion.query.filter_by(status=ContentSuggestion.STATUS_PENDING).count()
        self.assertEqual(pending_count_1, pending_count_2, "Must not create duplicate pending suggestions!")

        # Run 3
        suggs_3 = content_suggestion_agent.generate_suggestions(persist=True)
        reloaded_2 = db.session.get(ContentSuggestion, gap_id)
        self.assertEqual(reloaded_2.persistence_count, 3)
        self.assertIn("persisted for 3 scheduler run(s)", reloaded_2.reason)
        # Priority: (3 children * 2.0) + (3 runs * 5.0) = 21.0
        self.assertEqual(reloaded_2.priority_score, 21.0)
        pending_count_3 = ContentSuggestion.query.filter_by(status=ContentSuggestion.STATUS_PENDING).count()
        self.assertEqual(pending_count_1, pending_count_3, "Pending count must stay constant across runs!")

    def test_priority_score_calculation_and_sorting_in_admin_list(self):
        """Verify priority_score properly ranks critical gaps and admin UI orders by priority descending."""
        sugg_low = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_CONTENT_IMBALANCE,
            category_id=self.cat_logic.id,
            age_band='4-6',
            target_difficulty='Easy',
            suggested_title='Low Urgency Gap',
            reason='Minor gap affecting few children',
            priority_score=6.0,
            persistence_count=1,
            status=ContentSuggestion.STATUS_PENDING
        )
        sugg_high = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_PROGRESSION_GAP,
            category_id=self.cat_logic.id,
            age_band='9-12',
            target_difficulty='Advanced',
            suggested_title='Critical Urgency Bottleneck',
            reason='Critical gap affecting 20 children persisting for 4 runs',
            priority_score=60.0,
            persistence_count=4,
            status=ContentSuggestion.STATUS_PENDING
        )
        sugg_mid = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_AGE_COVERAGE_GAP,
            category_id=self.cat_visual.id,
            age_band='6-9',
            target_difficulty='Medium',
            suggested_title='Moderate Urgency Gap',
            reason='Moderate gap',
            priority_score=25.0,
            persistence_count=2,
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add_all([sugg_low, sugg_high, sugg_mid])
        db.session.commit()

        self.login_as(self.admin)
        res = self.client.get('/admin/content-suggestions')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Verify badges are rendered with formatted priority scores
        self.assertIn('⚡️ Priority: 60.0', html)
        self.assertIn('⚡️ Priority: 25.0', html)
        self.assertIn('⚡️ Priority: 6.0', html)

        # Verify ordering in HTML: High appears before Mid, and Mid appears before Low
        idx_high = html.find('Critical Urgency Bottleneck')
        idx_mid = html.find('Moderate Urgency Gap')
        idx_low = html.find('Low Urgency Gap')

        self.assertTrue(idx_high != -1 and idx_mid != -1 and idx_low != -1)
        self.assertLess(idx_high, idx_mid, "High priority suggestion should appear before mid priority")
        self.assertLess(idx_mid, idx_low, "Mid priority suggestion should appear before low priority")

    def test_engagement_trend_integration(self):
        """Verify analytics_service.compute_category_age_band_engagement_trend computes trends and influences priority."""
        child = Child(name='Trend Child', age=10, parent_id=self.parent.id)
        db.session.add(child)
        db.session.commit()

        act = Activity(
            category_id=self.cat_logic.id,
            title='Logic Trend Task',
            difficulty='Medium',
            min_age=9,
            max_age=12,
            is_active=True
        )
        db.session.add(act)
        db.session.commit()

        # Session 1 & 2: high accuracy (90%, 90%)
        # Session 3 & 4: low accuracy (50%, 50%) -> declining trend!
        t0 = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)

        s1 = ActivitySession(child_id=child.id, activity_id=act.id, accuracy=90.0, status=ActivitySession.STATUS_COMPLETED, start_time=t0, end_time=t0)
        s2 = ActivitySession(child_id=child.id, activity_id=act.id, accuracy=90.0, status=ActivitySession.STATUS_COMPLETED, start_time=t1, end_time=t1)
        s3 = ActivitySession(child_id=child.id, activity_id=act.id, accuracy=50.0, status=ActivitySession.STATUS_COMPLETED, start_time=t2, end_time=t2)
        s4 = ActivitySession(child_id=child.id, activity_id=act.id, accuracy=50.0, status=ActivitySession.STATUS_COMPLETED, start_time=t3, end_time=t3)

        db.session.add_all([s1, s2, s3, s4])
        db.session.commit()

        trend = analytics_service.compute_category_age_band_engagement_trend(self.cat_logic.id, '9-12')
        self.assertEqual(trend, 'declining')

        # Declining trend should add 5.0 urgency bonus in calculate_priority_score
        score_steady = content_suggestion_agent.calculate_priority_score(5, 1, 'steady')
        score_declining = content_suggestion_agent.calculate_priority_score(5, 1, 'declining')
        self.assertEqual(score_declining, score_steady + 5.0)

    # -------------------------------------------------------------------------
    # AI Reason Rephrasing & Numeric Validation Tests
    # -------------------------------------------------------------------------

    def test_validate_reason_numbers_exact_match(self):
        """Verify validate_reason_numbers returns True when exact numbers match in frequency."""
        # Progression gap numbers: 14 kids, ages 9-12, 82% accuracy, 1 activity, 3 runs
        expected = [14, 9, 12, 82, 1, 3]
        valid_sentence = (
            "Across 3 scheduler runs, 14 children aged 9-12 demonstrated an average accuracy of 82% "
            "in Medium Logic, while only 1 Advanced activity remains available."
        )
        self.assertTrue(content_suggestion_agent.validate_reason_numbers(valid_sentence, expected))

        # Dict format input
        expected_dict = {
            'affected_children': 14,
            'min_age': 9,
            'max_age': 12,
            'accuracy': 82,
            'available_activities': 1,
            'persistence_count': 3
        }
        self.assertTrue(content_suggestion_agent.validate_reason_numbers(valid_sentence, expected_dict))

    def test_validate_reason_numbers_missing_number_fails(self):
        """Verify validate_reason_numbers returns False if the text omits any required number."""
        expected = [14, 9, 12, 82, 1, 3]
        # Missing persistence count 3
        missing_runs = (
            "14 children aged 9-12 demonstrated an average accuracy of 82% "
            "in Medium Logic, while only 1 Advanced activity remains available."
        )
        self.assertFalse(content_suggestion_agent.validate_reason_numbers(missing_runs, expected))

    def test_validate_reason_numbers_extra_number_fails(self):
        """Verify validate_reason_numbers returns False if the text introduces an unprovided number."""
        expected = [14, 9, 12, 82, 1, 3]
        # Injects unprovided number 5
        extra_number = (
            "Across 3 scheduler runs, 14 children aged 9-12 in group 5 demonstrated an average accuracy of 82% "
            "in Medium Logic, while only 1 Advanced activity remains available."
        )
        self.assertFalse(content_suggestion_agent.validate_reason_numbers(extra_number, expected))

    def test_validate_reason_numbers_altered_number_fails(self):
        """Verify validate_reason_numbers returns False if a number was altered or rounded."""
        expected = [14, 9, 12, 82, 1, 3]
        # Altered 82 to 80
        altered_number = (
            "Across 3 scheduler runs, 14 children aged 9-12 demonstrated an average accuracy of 80% "
            "in Medium Logic, while only 1 Advanced activity remains available."
        )
        self.assertFalse(content_suggestion_agent.validate_reason_numbers(altered_number, expected))

    def test_validate_reason_numbers_spelled_words_fails(self):
        """Verify validate_reason_numbers returns False if digits are replaced with words."""
        expected = [14, 9, 12, 82, 1, 3]
        # Uses 'three' and 'one' instead of digits
        word_numbers = (
            "Across three scheduler runs, 14 children aged 9-12 demonstrated an average accuracy of 82% "
            "in Medium Logic, while only one Advanced activity remains available."
        )
        self.assertFalse(content_suggestion_agent.validate_reason_numbers(word_numbers, expected))

    def test_rephrase_reason_with_ai_fallback_on_invalid_numbers(self):
        """Verify rephrase_reason_with_ai discards AI text and falls back to template if numbers are altered."""
        template = (
            "14 children aged 9-12 are averaging 82% accuracy in Medium Logic with steady engagement, "
            "but only 1 Advanced activity(ies) available — this gap has persisted for 3 scheduler run(s)."
        )
        computed = {'affected': 14, 'min': 9, 'max': 12, 'acc': 82, 'acts': 1, 'runs': 3}

        # Mock Anthropic returning an altered number (80% instead of 82%)
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('app.agent.content_suggestion_agent._call_anthropic_api_rephrase') as mock_api:
                mock_api.return_value = (
                    "Across 3 scheduler runs, 14 children aged 9-12 achieved 80% accuracy in Medium Logic "
                    "with only 1 Advanced activity available."
                )
                result = content_suggestion_agent.rephrase_reason_with_ai(template, computed)
                self.assertEqual(result, template, "Must fall back to template reason when numbers do not match")

    def test_rephrase_reason_with_ai_fallback_on_missing_numbers(self):
        """Verify rephrase_reason_with_ai discards AI text and falls back to template if a number is missing."""
        template = (
            "14 children aged 9-12 are averaging 82% accuracy in Medium Logic with steady engagement, "
            "but only 1 Advanced activity(ies) available — this gap has persisted for 3 scheduler run(s)."
        )
        computed = {'affected': 14, 'min': 9, 'max': 12, 'acc': 82, 'acts': 1, 'runs': 3}

        # Mock Anthropic omitting the persistence count (3)
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('app.agent.content_suggestion_agent._call_anthropic_api_rephrase') as mock_api:
                mock_api.return_value = (
                    "14 children aged 9-12 achieved 82% accuracy in Medium Logic with only 1 Advanced activity available."
                )
                result = content_suggestion_agent.rephrase_reason_with_ai(template, computed)
                self.assertEqual(result, template, "Must fall back to template reason when a number is missing")

    def test_rephrase_reason_with_ai_success_on_valid_numbers(self):
        """Verify rephrase_reason_with_ai returns the AI-phrased text when all numbers match exactly."""
        template = (
            "14 children aged 9-12 are averaging 82% accuracy in Medium Logic with steady engagement, "
            "but only 1 Advanced activity(ies) available — this gap has persisted for 3 scheduler run(s)."
        )
        computed = {'affected': 14, 'min': 9, 'max': 12, 'acc': 82, 'acts': 1, 'runs': 3}
        ai_sentence = (
            "Across 3 scheduler runs, 14 children aged 9-12 demonstrated strong performance averaging 82% accuracy "
            "in Medium Logic, but currently only 1 Advanced challenge is available."
        )

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('app.agent.content_suggestion_agent._call_anthropic_api_rephrase') as mock_api:
                mock_api.return_value = ai_sentence
                result = content_suggestion_agent.rephrase_reason_with_ai(template, computed)
                self.assertEqual(result, ai_sentence, "Must adopt the AI-rephrased reason when all numbers match")

    def test_rephrase_reason_with_ai_fallback_when_api_key_unset(self):
        """Verify rephrase_reason_with_ai immediately returns template reason when ANTHROPIC_API_KEY is not set."""
        template = "2 registered learner(s) in age band 4-6 currently have only 0 activity(ies) available in 'Visual Learning'."
        computed = {'affected': 2, 'min': 4, 'max': 6, 'acts': 0, 'runs': 1}

        with patch.dict(os.environ, {}, clear=True):
            result = content_suggestion_agent.rephrase_reason_with_ai(template, computed)
            self.assertEqual(result, template)

    def test_rephrase_reason_with_ai_compliance_fallback(self):
        """Verify rephrase_reason_with_ai discards AI text and falls back to template if clinical terms appear."""
        template = "14 children aged 9-12 are averaging 82% accuracy in Medium Logic with only 1 activity available."
        computed = {'affected': 14, 'min': 9, 'max': 12, 'acc': 82, 'acts': 1}

        # AI text includes forbidden term 'deficit'
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('app.agent.content_suggestion_agent._call_anthropic_api_rephrase') as mock_api:
                mock_api.return_value = (
                    "Across 14 children aged 9-12 with 82% accuracy, there is a deficit with only 1 activity available."
                )
                result = content_suggestion_agent.rephrase_reason_with_ai(template, computed)
                self.assertEqual(result, template, "Must block clinical terms and fall back to template")

    def test_generate_suggestions_uses_rephrased_reason_when_ai_valid(self):
        """Verify generate_suggestions applies AI rephrasing when valid and falls back when numbers are invalid."""
        # Create a child to trigger an age coverage gap
        teen = Child(name='Zane Teen', age=13, parent_id=self.parent.id)
        db.session.add(teen)
        db.session.commit()

        # Zane is age 13 -> age band 12-14. Visual Learning has 0 activities.
        # Template reason has numbers: 1 (learner), 12, 14 (ages), 0 (acts), 1 (runs).
        valid_rephrase = (
            "Across 1 scheduler run, 1 registered learner in age band 12-14 has only 0 activities available in Visual Learning."
        )

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('app.agent.content_suggestion_agent._call_anthropic_api_rephrase') as mock_api:
                mock_api.return_value = valid_rephrase
                suggestions = content_suggestion_agent.generate_suggestions(persist=False)
                visual_gap = next((s for s in suggestions if s.category_id == self.cat_visual.id and s.age_band == '12-14'), None)
                self.assertIsNotNone(visual_gap)
                self.assertEqual(visual_gap.reason, valid_rephrase)

        # Now test with invalid numbers (e.g. AI invents 99)
        invalid_rephrase = (
            "Across 1 scheduler run, 99 registered learners in age band 12-14 have only 0 activities available in Visual Learning."
        )
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('app.agent.content_suggestion_agent._call_anthropic_api_rephrase') as mock_api:
                mock_api.return_value = invalid_rephrase
                suggestions = content_suggestion_agent.generate_suggestions(persist=False)
                visual_gap = next((s for s in suggestions if s.category_id == self.cat_visual.id and s.age_band == '12-14'), None)
                self.assertIsNotNone(visual_gap)
                self.assertNotEqual(visual_gap.reason, invalid_rephrase)
                self.assertIn("registered learner(s) in age band 12-14", visual_gap.reason)


if __name__ == '__main__':
    unittest.main()

