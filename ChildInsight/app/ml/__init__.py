"""Machine learning package for pattern clustering and feature vectors."""
from app.ml.features import (
    FEATURE_NAMES,
    DOMAIN_CATEGORIES,
    build_child_feature_vector,
    get_child_feature_dict,
    build_feature_matrix_for_children
)
from app.ml.clustering import (
    DEFAULT_RANDOM_STATE,
    generate_cluster_label_from_centroid,
    cluster_interaction_patterns
)
from app.ml.model_manager import (
    MIN_CHILDREN_FOR_CLUSTERING,
    PatternModelManager,
    fit_model,
    predict_child_cluster,
    get_model_manager
)

__all__ = [
    'FEATURE_NAMES',
    'DOMAIN_CATEGORIES',
    'build_child_feature_vector',
    'get_child_feature_dict',
    'build_feature_matrix_for_children',
    'DEFAULT_RANDOM_STATE',
    'generate_cluster_label_from_centroid',
    'cluster_interaction_patterns',
    'MIN_CHILDREN_FOR_CLUSTERING',
    'PatternModelManager',
    'fit_model',
    'predict_child_cluster',
    'get_model_manager'
]
