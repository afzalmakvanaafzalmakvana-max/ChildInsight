import unittest
import numpy as np
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity
from app.models.session import ActivitySession
from app.utils.seed_data import seed_activities
from app.ml.features import (
    FEATURE_NAMES,
    build_child_feature_vector,
    get_child_feature_dict,
    build_feature_matrix_for_children
)
from app.ml.clustering import (
    cluster_interaction_patterns,
    generate_cluster_label_from_centroid
)
from app.ml.model_manager import (
    PatternModelManager,
    MIN_CHILDREN_FOR_CLUSTERING
)
from app.services import profile_service


class Phase7MachineLearningTestCase(unittest.TestCase):
    """Automated test suite verifying Phase 7 Machine Learning (features, K-Means clustering, and Learning Pattern Engine)."""

    FORBIDDEN_DIAGNOSTIC_TERMS = [
        'adhd', 'autism', 'dyslexia', 'disorder', 'syndrome', 'deficit',
        'abnormal', 'impaired', 'pathology', 'iq', 'retarded', 'handicap',
        'clinical', 'diagnosis', 'medical', 'mentally', 'retardation',
        'subnormal', 'disease', 'handicapped', 'psychiatric'
    ]

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed categories and activities
        seed_activities()
        self.categories = {cat.slug: cat for cat in Category.query.all()}
        self.activities = {cat.slug: Activity.query.filter_by(category_id=cat.id).all() for cat in self.categories.values()}

        # Seed parent and test children
        self.parent = User(name='Parent ML', email='parent_ml@example.com', role='parent')
        self.parent.set_password('Pass123!')
        db.session.add(self.parent)
        db.session.commit()

        # Create 4 children for clustering
        self.child_visual = Child(parent_id=self.parent.id, name='Alex (Visual)', age=6, grade='1st')
        self.child_logic = Child(parent_id=self.parent.id, name='Blake (Logic)', age=7, grade='2nd')
        self.child_memory = Child(parent_id=self.parent.id, name='Charlie (Memory)', age=6, grade='1st')
        self.child_new = Child(parent_id=self.parent.id, name='Dana (New)', age=5, grade='K')
        db.session.add_all([self.child_visual, self.child_logic, self.child_memory, self.child_new])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _create_completed_session(self, child_id, activity, accuracy, attempts=5):
        """Helper to create a completed session with specific accuracy and attempts."""
        correct = int(round((accuracy / 100.0) * attempts))
        session = ActivitySession(
            child_id=child_id,
            activity_id=activity.id,
            attempts=attempts,
            correct_answers=correct,
            accuracy=accuracy,
            duration_seconds=120,
            status=ActivitySession.STATUS_COMPLETED
        )
        db.session.add(session)
        db.session.commit()
        return session

    # --- 1. Feature Vector Extraction Tests ---

    def test_feature_vector_building_correctness(self):
        """Verify numeric feature vector per child contains Visual, Memory, Logic, Number, Language, Engagement scores (0-100)."""
        # Create sessions for Alex: Visual 90%, Memory 80%, Others 0%
        vis_act = self.activities['visual'][0]
        mem_act = self.activities['memory'][0]
        self._create_completed_session(self.child_visual.id, vis_act, accuracy=90.0, attempts=10)
        self._create_completed_session(self.child_visual.id, mem_act, accuracy=80.0, attempts=10)

        feat_dict = get_child_feature_dict(self.child_visual.id)

        # Check all 6 keys present
        for expected_key in FEATURE_NAMES:
            self.assertIn(expected_key, feat_dict)

        self.assertAlmostEqual(feat_dict['visual'], 90.0, delta=1.0)
        self.assertAlmostEqual(feat_dict['memory'], 80.0, delta=1.0)
        self.assertAlmostEqual(feat_dict['logic'], 0.0, delta=0.1)
        self.assertGreater(feat_dict['engagement'], 0.0)

        # Verify numpy vector representation
        vec = build_child_feature_vector(self.child_visual.id)
        self.assertIsInstance(vec, np.ndarray)
        self.assertEqual(vec.shape, (6,))
        for score in vec:
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 100.0)

    def test_feature_vector_for_child_without_sessions(self):
        """A new child with zero sessions returns baseline 0.0 scores."""
        vec = build_child_feature_vector(self.child_new.id)
        self.assertEqual(vec.shape, (6,))
        self.assertTrue(np.all(vec == 0.0))

    # --- 2. Programmatic Centroid Labelling & K-Means Clustering Tests ---

    def test_programmatic_centroid_label_generation(self):
        """Verify cluster labels are generated dynamically from centroids and never hardcoded."""
        # Visual + Memory dominant centroid
        # Ordering: ['visual', 'memory', 'logic', 'number', 'language', 'engagement']
        centroid_vis_mem = np.array([88.0, 82.0, 40.0, 35.0, 45.0, 75.0])
        meta_vm = generate_cluster_label_from_centroid(centroid_vis_mem)
        self.assertIn("Visual", meta_vm['label'])
        self.assertIn("Memory", meta_vm['label'])
        self.assertIn("Strong Interaction", meta_vm['label'])

        # Logic focused centroid
        centroid_logic = np.array([30.0, 40.0, 92.0, 45.0, 35.0, 70.0])
        meta_logic = generate_cluster_label_from_centroid(centroid_logic)
        self.assertIn("Logic", meta_logic['label'])
        self.assertIn("Focused Interaction", meta_logic['label'])

        # Balanced centroid
        centroid_balanced = np.array([75.0, 78.0, 74.0, 76.0, 77.0, 80.0])
        meta_balanced = generate_cluster_label_from_centroid(centroid_balanced)
        self.assertIn("Balanced", meta_balanced['label'])

    def test_kmeans_clustering_runs_and_labels_children(self):
        """Verify K-Means clustering groups synthetic feature matrices into labeled clusters."""
        # 6 samples across 2 distinct patterns
        matrix = np.array([
            [85.0, 80.0, 30.0, 25.0, 30.0, 70.0],
            [90.0, 85.0, 35.0, 20.0, 25.0, 75.0],
            [82.0, 78.0, 28.0, 32.0, 30.0, 68.0],
            [25.0, 30.0, 88.0, 82.0, 35.0, 72.0],
            [30.0, 25.0, 92.0, 85.0, 40.0, 78.0],
            [28.0, 35.0, 85.0, 80.0, 32.0, 70.0]
        ])

        result = cluster_interaction_patterns(matrix, n_clusters=2, random_state=42)
        self.assertEqual(len(result['cluster_meta']), 2)
        self.assertEqual(len(result['cluster_assignments']), 6)

        # Labels must be non-empty strings
        for cluster_id, meta in result['cluster_meta'].items():
            self.assertIsInstance(meta['label'], str)
            self.assertGreater(len(meta['label']), 5)

    # --- 3. Cold-Start Handling in Model Manager ---

    def test_cold_start_fallback_with_few_children(self):
        """Model manager gracefully returns cold-start status when fewer than 3 children have sessions."""
        # Only 1 child has a session
        vis_act = self.activities['visual'][0]
        self._create_completed_session(self.child_visual.id, vis_act, accuracy=85.0)

        manager = PatternModelManager(n_clusters=3, random_state=42)
        fit_result = manager.fit()

        self.assertEqual(fit_result['status'], 'cold_start')
        self.assertFalse(fit_result['is_fitted'])
        self.assertIn('Not enough data yet', fit_result['message'])

        # Predict for child in cold start returns fallback response
        pred = manager.predict_child_cluster(self.child_visual.id)
        self.assertTrue(pred['is_fallback'])
        self.assertEqual(pred['cluster_id'], -1)
        self.assertIn('Not enough data yet', pred['reason'])

    # --- 4. Single Child Cluster Prediction with Sufficient Cohort ---

    def test_single_child_cluster_prediction_when_trained(self):
        """Verify model fitting and cluster prediction once sufficient children have activity records."""
        # Child 1: Strong in Visual & Memory
        self._create_completed_session(self.child_visual.id, self.activities['visual'][0], accuracy=95.0)
        self._create_completed_session(self.child_visual.id, self.activities['memory'][0], accuracy=90.0)

        # Child 2: Strong in Logic & Numbers
        self._create_completed_session(self.child_logic.id, self.activities['logic'][0], accuracy=95.0)
        self._create_completed_session(self.child_logic.id, self.activities['numbers'][0], accuracy=90.0)

        # Child 3: Strong in Memory & Language
        self._create_completed_session(self.child_memory.id, self.activities['memory'][0], accuracy=92.0)
        self._create_completed_session(self.child_memory.id, self.activities['language'][0], accuracy=88.0)

        manager = PatternModelManager(n_clusters=3, random_state=42)
        fit_result = manager.fit()

        self.assertTrue(fit_result['is_fitted'])
        self.assertEqual(fit_result['status'], 'success')

        # Predict for Child Visual
        pred_visual = manager.predict_child_cluster(self.child_visual.id)
        self.assertFalse(pred_visual['is_fallback'])
        self.assertGreaterEqual(pred_visual['cluster_id'], 0)
        self.assertIsInstance(pred_visual['pattern_group'], str)
        self.assertIn('Interaction', pred_visual['pattern_group'])

    # --- 5. Learning Pattern Engine Plain-Language Observation ---

    def test_learning_pattern_engine_plain_language_observation(self):
        """Verify the Learning Pattern Engine produces friendly educational observation sentences."""
        # Give Child Visual high visual and memory scores
        self._create_completed_session(self.child_visual.id, self.activities['visual'][0], accuracy=92.0)
        self._create_completed_session(self.child_visual.id, self.activities['memory'][0], accuracy=88.0)

        # Seed other children to meet clustering threshold
        self._create_completed_session(self.child_logic.id, self.activities['logic'][0], accuracy=90.0)
        self._create_completed_session(self.child_memory.id, self.activities['numbers'][0], accuracy=85.0)

        # Call Learning Pattern Engine service
        profile = profile_service.get_child_learning_pattern_observation(self.child_visual.id)

        self.assertIn('observation', profile)
        obs = profile['observation']
        self.assertIsInstance(obs, str)
        self.assertGreater(len(obs), 20)
        self.assertIn("Recent sessions show", obs)
        self.assertIn("visual", obs.lower())

    # --- 6. Ethical Safeguards: Zero Diagnostic/Clinical Language ---

    def test_zero_diagnostic_or_clinical_language_in_ml_outputs(self):
        """Core Ethical Mandate: verify that no diagnostic or clinical labels appear in cluster labels or observations."""
        # Seed diverse sessions
        self._create_completed_session(self.child_visual.id, self.activities['visual'][0], accuracy=80.0)
        self._create_completed_session(self.child_logic.id, self.activities['logic'][0], accuracy=40.0)
        self._create_completed_session(self.child_memory.id, self.activities['numbers'][0], accuracy=20.0)

        manager = PatternModelManager(n_clusters=3, random_state=42)
        manager.fit()

        all_texts_to_check = []

        # Check all cluster meta labels
        for meta in manager.cluster_meta.values():
            all_texts_to_check.append(meta.get('label', ''))

        # Check observations across all children
        for cid in [self.child_visual.id, self.child_logic.id, self.child_memory.id, self.child_new.id]:
            obs_payload = profile_service.get_child_learning_pattern_observation(cid)
            all_texts_to_check.append(obs_payload['pattern_group'])
            all_texts_to_check.append(obs_payload['observation'])

        self.assertGreater(len(all_texts_to_check), 0)

        for text in all_texts_to_check:
            lower_text = text.lower()
            for forbidden in self.FORBIDDEN_DIAGNOSTIC_TERMS:
                self.assertNotIn(
                    forbidden,
                    lower_text,
                    f"Forbidden diagnostic term '{forbidden}' detected in ML output: '{text}'"
                )


if __name__ == '__main__':
    unittest.main()
