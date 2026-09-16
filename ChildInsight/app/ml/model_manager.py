import numpy as np
from app.models.child import Child
from app.models.session import ActivitySession
from app.ml.features import build_child_feature_vector, get_child_feature_dict, build_feature_matrix_for_children
from app.ml.clustering import cluster_interaction_patterns, DEFAULT_RANDOM_STATE

MIN_CHILDREN_FOR_CLUSTERING = 3
DEFAULT_N_CLUSTERS = 3


class PatternModelManager:
    """Manages the lifecycle, fitting, caching, and inference of the learning interaction K-Means model."""

    def __init__(self, n_clusters=DEFAULT_N_CLUSTERS, random_state=DEFAULT_RANDOM_STATE):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.model = None
        self.cluster_meta = {}
        self.is_fitted = False
        self.fitted_child_ids = []

    def get_eligible_children_ids(self):
        """Returns IDs of children who have at least one recorded activity session."""
        active_child_ids = [
            row[0] for row in
            ActivitySession.query.with_entities(ActivitySession.child_id).distinct().all()
        ]
        return active_child_ids

    def fit(self, force=False):
        """Fits the K-Means clustering model on all eligible children with session data."""
        child_ids = self.get_eligible_children_ids()

        # Cold-start check: insufficient children to cluster
        if len(child_ids) < MIN_CHILDREN_FOR_CLUSTERING:
            self.is_fitted = False
            self.model = None
            self.cluster_meta = {}
            self.fitted_child_ids = []
            return {
                'status': 'cold_start',
                'is_fitted': False,
                'message': 'Not enough data yet to form cluster patterns (minimum 3 learners with session history required).',
                'active_children_count': len(child_ids),
                'min_required': MIN_CHILDREN_FOR_CLUSTERING
            }

        feature_matrix, valid_ids = build_feature_matrix_for_children(child_ids)
        if len(valid_ids) < MIN_CHILDREN_FOR_CLUSTERING:
            self.is_fitted = False
            return {
                'status': 'cold_start',
                'is_fitted': False,
                'message': 'Not enough data yet (insufficient valid feature vectors).',
                'active_children_count': len(valid_ids),
                'min_required': MIN_CHILDREN_FOR_CLUSTERING
            }

        k = min(self.n_clusters, len(valid_ids))
        cluster_result = cluster_interaction_patterns(
            feature_matrix=feature_matrix,
            n_clusters=k,
            random_state=self.random_state
        )

        self.model = cluster_result['model']
        self.cluster_meta = cluster_result['cluster_meta']
        self.is_fitted = True
        self.fitted_child_ids = valid_ids

        return {
            'status': 'success',
            'is_fitted': True,
            'message': f'Fitted clustering model successfully with {k} pattern groups.',
            'n_clusters': k,
            'active_children_count': len(valid_ids),
            'cluster_meta': self.cluster_meta
        }

    def predict_child_cluster(self, child_id):
        """Predicts the interaction pattern cluster and label for a single child."""
        features_dict = get_child_feature_dict(child_id)
        vec = build_child_feature_vector(child_id).reshape(1, -1)

        # Check child's personal activity count
        has_sessions = ActivitySession.query.filter_by(child_id=child_id).first() is not None
        if not has_sessions:
            return {
                'child_id': child_id,
                'cluster_id': -1,
                'pattern_group': 'Introductory Exploration',
                'is_fallback': True,
                'reason': 'Not enough data yet (no activity sessions recorded for this learner).',
                'features': features_dict,
                'cluster_meta': None
            }

        # Auto-fit if not yet fitted
        if not self.is_fitted:
            fit_res = self.fit()
            if not fit_res['is_fitted']:
                return {
                    'child_id': child_id,
                    'cluster_id': -1,
                    'pattern_group': 'Baseline Interaction Pattern',
                    'is_fallback': True,
                    'reason': 'Not enough data yet to form cluster patterns across the cohort.',
                    'features': features_dict,
                    'cluster_meta': None
                }

        # Predict cluster assignment
        cluster_idx = int(self.model.predict(vec)[0])
        meta = self.cluster_meta.get(cluster_idx, {})

        return {
            'child_id': child_id,
            'cluster_id': cluster_idx,
            'pattern_group': meta.get('label', 'General Interaction Pattern'),
            'is_fallback': False,
            'reason': f"Grouped into '{meta.get('label')}' based on activity interaction centroid.",
            'features': features_dict,
            'cluster_meta': meta
        }


# Global default manager instance
_default_manager = PatternModelManager()


def fit_model(force=False):
    """Module-level helper to trigger model fitting across eligible children."""
    return _default_manager.fit(force=force)


def predict_child_cluster(child_id):
    """Module-level helper to predict cluster and pattern group for a single child."""
    return _default_manager.predict_child_cluster(child_id)


def get_model_manager():
    """Returns the active model manager singleton."""
    return _default_manager
