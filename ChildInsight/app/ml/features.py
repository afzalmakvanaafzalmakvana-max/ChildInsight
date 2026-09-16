import numpy as np
from app.services import analytics_service, engagement_service

FEATURE_NAMES = ['visual', 'memory', 'logic', 'number', 'language', 'engagement']
DOMAIN_CATEGORIES = ['visual', 'memory', 'logic', 'number', 'language']

# Mapping from category slug in database to feature dimension
SLUG_MAP = {
    'visual': 'visual',
    'memory': 'memory',
    'logic': 'logic',
    'numbers': 'number',
    'language': 'language'
}


def _clamp_score(val):
    """Clamps numeric score to valid [0.0, 100.0] range."""
    try:
        f = float(val)
        return min(100.0, max(0.0, f))
    except (ValueError, TypeError):
        return 0.0


def get_child_feature_dict(child_id_or_snapshot):
    """Returns a named dictionary of the 6 core educational feature dimensions for a child."""
    if isinstance(child_id_or_snapshot, dict):
        snapshot = child_id_or_snapshot
    else:
        snapshot = analytics_service.get_child_analytics_snapshot(child_id_or_snapshot)

    category_breakdown = snapshot.get('category_breakdown', {})
    features = {}

    # Extract domain accuracy scores (0.0 - 100.0)
    for slug, feat_key in SLUG_MAP.items():
        cat_info = category_breakdown.get(slug, {})
        acc = cat_info.get('accuracy', 0.0)
        features[feat_key] = _clamp_score(acc)

    # Extract overall engagement score (0.0 - 100.0)
    features['engagement'] = _clamp_score(snapshot.get('engagement_index', 0.0))

    return features


def build_child_feature_vector(child_id_or_snapshot):
    """Builds a 1D numpy array representing a child's 6-dimensional interaction feature vector."""
    feat_dict = get_child_feature_dict(child_id_or_snapshot)
    vec = [feat_dict[name] for name in FEATURE_NAMES]
    return np.array(vec, dtype=float)


def build_feature_matrix_for_children(child_ids):
    """Builds an (N, 6) feature matrix for a collection of children, filtering out invalid records."""
    vectors = []
    valid_ids = []

    for cid in child_ids:
        try:
            vec = build_child_feature_vector(cid)
            vectors.append(vec)
            valid_ids.append(cid)
        except Exception:
            continue

    if not vectors:
        return np.empty((0, len(FEATURE_NAMES)), dtype=float), []

    return np.vstack(vectors), valid_ids
