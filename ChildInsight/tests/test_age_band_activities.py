import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.utils.seed_data import seed_activities


class AgeBandActivitiesTestCase(unittest.TestCase):
    """Automated tests confirming age-band filtering for children aged 4-14."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create parent user
        self.parent = User(name='Jordan Parent', email='jordan@example.com', role='parent', is_active=True)
        self.parent.set_password('Password123!')
        db.session.add(self.parent)
        db.session.commit()

        # Create children across different age bands
        self.child_preschool = Child(name='Ella Preschool', age=5, grade='Pre-K', parent_id=self.parent.id)
        self.child_early_elem = Child(name='Leo Elementary', age=7, grade='2nd', parent_id=self.parent.id)
        self.child_upper_elem = Child(name='Mia Middle', age=10, grade='5th', parent_id=self.parent.id)
        self.child_secondary = Child(name='Zane Teen', age=13, grade='8th', parent_id=self.parent.id)
        self.child_no_age = Child(name='Sam Explorer', age=None, grade=None, parent_id=self.parent.id)

        db.session.add_all([
            self.child_preschool,
            self.child_early_elem,
            self.child_upper_elem,
            self.child_secondary,
            self.child_no_age
        ])
        db.session.commit()

        # Seed the activity database
        seed_activities()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_as_parent(self):
        return self.client.post('/auth/login', data={
            'email': 'jordan@example.com',
            'password': 'Password123!'
        }, follow_redirects=True)

    def test_activity_model_age_fields_and_property(self):
        """Confirm Activity model persists min_age and max_age with age_band property."""
        cat = Category.query.first()
        act = Activity(
            category_id=cat.id,
            title='Custom Rocket [Demo Data]',
            difficulty='Easy',
            min_age=6,
            max_age=9
        )
        db.session.add(act)
        db.session.commit()

        loaded = db.session.get(Activity, act.id)
        self.assertEqual(loaded.min_age, 6)
        self.assertEqual(loaded.max_age, 9)
        self.assertEqual(loaded.age_band, '6-9')

    def test_preschool_child_only_sees_ages_4_to_6_activities(self):
        """Confirm a 5-year-old child only sees activities where min_age <= 5 <= max_age."""
        self.login_as_parent()
        cat = Category.query.filter_by(slug='visual').first()

        res = self.client.get(f'/child/{self.child_preschool.id}/category/{cat.id}')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Should contain age 4-6 activities
        self.assertIn('Color Match Adventure', html)
        self.assertIn('Shape Explorer', html)
        self.assertIn('Rainbow Sorting Quest', html)
        self.assertIn('Tiny Critter Camouflage', html)

        # Must NOT contain older age band activities (strictly omitted, not greyed out)
        self.assertNotIn('Complex Matrix Reasoning', html)
        self.assertNotIn('Origami Geometry Lab', html)
        self.assertNotIn('Spatial Navigator', html)
        self.assertNotIn('3D Cube Rotation', html)

    def test_secondary_child_only_sees_ages_12_to_14_activities(self):
        """Confirm a 13-year-old child only sees activities where min_age <= 13 <= max_age."""
        self.login_as_parent()
        cat = Category.query.filter_by(slug='logic').first()

        res = self.client.get(f'/child/{self.child_secondary.id}/category/{cat.id}')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Should contain 12-14 advanced logic challenges
        self.assertIn('Deductive Logic Grid', html)
        self.assertIn('Syllogism Explorer', html)
        self.assertIn('Multi-Constraint Escape', html)

        # Must NOT contain early childhood 4-6 activities
        self.assertNotIn('Animal Friends', html)
        self.assertNotIn('Day and Night', html)
        self.assertNotIn('Who Belongs Where?', html)

    def test_early_elementary_child_only_sees_ages_6_to_9_activities(self):
        """Confirm a 7-year-old child only sees 6-9 activities."""
        self.login_as_parent()
        cat = Category.query.filter_by(slug='numbers').first()

        res = self.client.get(f'/child/{self.child_early_elem.id}/category/{cat.id}')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Should contain 6-9 number activities
        self.assertIn('Addition Journey', html)
        self.assertIn('Number Pattern Quest', html)
        self.assertIn('Friendly Double Magic', html)

        # Must NOT contain 12-14 algebra or probability
        self.assertNotIn('Pre-Algebra Mystery X', html)
        self.assertNotIn('Probability Carnival', html)
        # Must NOT contain preschool 4-6 finger counting
        self.assertNotIn('Finger Tap Counting', html)

    def test_upper_elementary_child_only_sees_ages_9_to_12_activities(self):
        """Confirm a 10-year-old child only sees 9-12 activities."""
        self.login_as_parent()
        cat = Category.query.filter_by(slug='language').first()

        res = self.client.get(f'/child/{self.child_upper_elem.id}/category/{cat.id}')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Should contain 9-12 language activities
        self.assertIn('Context Clue Sleuth', html)
        self.assertIn('Metaphor &amp; Simile Sparks', html)
        self.assertIn('Word Roots &amp; Prefixes', html)

        # Must NOT contain preschool letter sounds or secondary rhetoric
        self.assertNotIn('Letter Sounds', html)
        self.assertNotIn('Alphabet Safari', html)
        self.assertNotIn('Rhetorical Devices Quest', html)

    def test_child_without_age_sees_all_activities(self):
        """Confirm a child with age=None falls back to showing all active activities."""
        self.login_as_parent()
        cat = Category.query.filter_by(slug='visual').first()

        res = self.client.get(f'/child/{self.child_no_age.id}/category/{cat.id}')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Should include both preschool and secondary activities
        self.assertIn('Color Match Adventure', html)
        self.assertIn('Complex Matrix Reasoning', html)

    def test_all_categories_have_complete_age_band_coverage(self):
        """Verify that every category has activities seeded for all 4 age bands."""
        categories = Category.query.all()
        self.assertEqual(len(categories), 5)

        age_bands = [(4, 6), (6, 9), (9, 12), (12, 14)]
        for cat in categories:
            for min_a, max_a in age_bands:
                matching_count = Activity.query.filter_by(
                    category_id=cat.id,
                    min_age=min_a,
                    max_age=max_a,
                    is_active=True
                ).count()
                self.assertGreaterEqual(
                    matching_count,
                    3,
                    f"Category {cat.name} must have at least 3 activities for age band {min_a}-{max_a}, found {matching_count}"
                )

    def test_expanded_seeded_activities_and_questions_counts(self):
        """Confirm exactly 115 activities and 415 questions seeded across all 5 categories."""
        # 1. Expected overall counts
        self.assertEqual(Activity.query.count(), 115)
        self.assertEqual(ActivityQuestion.query.count(), 415)

        # 2. Confirm each category has 23 activities (19 previously + 4 expanded)
        categories = Category.query.all()
        self.assertEqual(len(categories), 5)
        for cat in categories:
            cat_acts = Activity.query.filter_by(category_id=cat.id).all()
            self.assertEqual(len(cat_acts), 23, f"Category {cat.name} must have 23 activities")

            # 3. Confirm all 4 difficulty levels exist in every category
            difficulties = set(a.difficulty for a in cat_acts)
            self.assertSetEqual(
                difficulties,
                {'Beginner', 'Easy', 'Medium', 'Advanced'},
                f"Category {cat.name} missing difficulty tiers"
            )

        # 4. Confirm demo tagging on all activities
        demo_acts = Activity.query.filter_by(is_demo=True).all()
        self.assertEqual(len(demo_acts), 115)
        for act in demo_acts:
            self.assertIn('[Demo Data]', act.title)

        # 5. Confirm activities each have between 3 and 6 questions (new ones have 5 questions)
        for act in Activity.query.all():
            q_count = act.questions.count()
            self.assertTrue(
                3 <= q_count <= 6,
                f"Activity {act.title} question count {q_count} outside expected range"
            )

    def test_zero_activity_overlap_between_preschool_and_secondary_across_platform(self):
        """Verify zero activity overlap between age 5 (preschool) and age 13 (secondary) across all categories."""
        # Query visible activities for age 5
        acts_5 = Activity.query.filter(
            Activity.is_active.is_(True),
            Activity.min_age <= self.child_preschool.age,
            Activity.max_age >= self.child_preschool.age
        ).all()

        # Query visible activities for age 13
        acts_13 = Activity.query.filter(
            Activity.is_active.is_(True),
            Activity.min_age <= self.child_secondary.age,
            Activity.max_age >= self.child_secondary.age
        ).all()

        ids_5 = {a.id for a in acts_5}
        ids_13 = {a.id for a in acts_13}
        shared_ids = ids_5.intersection(ids_13)

        # Confirm zero shared activities
        self.assertEqual(len(shared_ids), 0, f"Found unexpected shared activities between 5yo and 13yo: {shared_ids}")

        # Confirm 5yo sees 0 secondary activities and 13yo sees 0 preschool activities
        self.assertTrue(all(a.max_age < 12 for a in acts_5), "5yo sees activities meant for secondary (12-14)")
        self.assertTrue(all(a.min_age > 6 for a in acts_13), "13yo sees activities meant for preschool (4-6)")

    def test_recommendations_strictly_respect_child_age_band(self):
        """Verify recommendation engine suggests age-appropriate content for 5yo and 13yo with zero overlap."""
        from app.services.recommendation_service import get_recommendations_for_child

        # 5yo preschool recommendations
        recs_5 = get_recommendations_for_child(self.child_preschool.id, persist=False)
        self.assertGreater(len(recs_5), 0)
        for r in recs_5:
            act = db.session.get(Activity, r['activity_id'])
            self.assertTrue(
                act.min_age <= self.child_preschool.age <= act.max_age,
                f"Preschool child received out-of-band recommendation: {act.title} (Ages {act.min_age}-{act.max_age})"
            )

        # 13yo secondary recommendations
        recs_13 = get_recommendations_for_child(self.child_secondary.id, persist=False)
        self.assertGreater(len(recs_13), 0)
        for r in recs_13:
            act = db.session.get(Activity, r['activity_id'])
            self.assertTrue(
                act.min_age <= self.child_secondary.age <= act.max_age,
                f"Secondary child received out-of-band recommendation: {act.title} (Ages {act.min_age}-{act.max_age})"
            )

        # Zero overlap between recommendations
        act_ids_5 = {r['activity_id'] for r in recs_5}
        act_ids_13 = {r['activity_id'] for r in recs_13}
        self.assertEqual(len(act_ids_5.intersection(act_ids_13)), 0)

    def test_difficulty_progression_scenarios_and_reason_strings(self):
        """Verify 90%, 60%, and 30% accuracy evaluate to logical, distinct difficulty progressions with reasons."""
        from app.services.recommendation_service import (
            evaluate_rule_based_recommendation,
            evaluate_performance_based_recommendation
        )

        # Scenario 1: High Performer (90% accuracy)
        rule_90 = evaluate_rule_based_recommendation(90.0, current_difficulty='Easy', category_name='Logic')
        self.assertEqual(rule_90['recommendation_type'], 'level_up')
        self.assertEqual(rule_90['target_difficulty'], 'Medium')
        self.assertIn('Medium level', rule_90['reason'])

        perf_90 = evaluate_performance_based_recommendation(90.0, 100.0, current_difficulty='Easy', category_name='Logic')
        self.assertEqual(perf_90['recommendation_type'], 'level_up')
        self.assertEqual(perf_90['target_difficulty'], 'Medium')
        self.assertIn('Medium level', perf_90['reason'])

        # Scenario 2: Steady Learner (60% accuracy)
        rule_60 = evaluate_rule_based_recommendation(60.0, current_difficulty='Easy', category_name='Logic')
        self.assertEqual(rule_60['recommendation_type'], 'reinforce')
        self.assertEqual(rule_60['target_difficulty'], 'Easy')
        self.assertIn('Easy activity', rule_60['reason'])

        perf_60 = evaluate_performance_based_recommendation(60.0, 100.0, current_difficulty='Easy', category_name='Logic')
        self.assertEqual(perf_60['recommendation_type'], 'reinforce')
        self.assertEqual(perf_60['target_difficulty'], 'Easy')
        self.assertIn('Easy level', perf_60['reason'])

        # Scenario 3: Struggling Learner (30% accuracy)
        rule_30 = evaluate_rule_based_recommendation(30.0, current_difficulty='Easy', category_name='Logic')
        self.assertEqual(rule_30['recommendation_type'], 'practice')
        self.assertEqual(rule_30['target_difficulty'], 'Beginner')
        self.assertIn('Beginner activities', rule_30['reason'])

        perf_30 = evaluate_performance_based_recommendation(30.0, 100.0, current_difficulty='Easy', category_name='Logic')
        self.assertEqual(perf_30['recommendation_type'], 'practice')
        self.assertEqual(perf_30['target_difficulty'], 'Beginner')
        self.assertIn('Beginner activities', perf_30['reason'])

        # Assert monotonicity: 90% difficulty > 60% difficulty > 30% difficulty
        difficulty_order = ['Beginner', 'Easy', 'Medium', 'Advanced']
        idx_90 = difficulty_order.index(perf_90['target_difficulty'])
        idx_60 = difficulty_order.index(perf_60['target_difficulty'])
        idx_30 = difficulty_order.index(perf_30['target_difficulty'])
        self.assertGreater(idx_90, idx_60)
        self.assertGreater(idx_60, idx_30)


if __name__ == '__main__':
    unittest.main()


