from app.ml import model_manager
from app.ml.features import DOMAIN_CATEGORIES

DOMAIN_LABELS = {
    'visual': 'visual',
    'memory': 'memory',
    'logic': 'logic',
    'number': 'number',
    'language': 'language'
}


def get_child_learning_pattern_observation(child_id):
    """Learning Pattern Engine: Converts numeric metrics and interaction cluster into plain-language educational observations."""
    prediction = model_manager.predict_child_cluster(child_id)
    features = prediction.get('features', {})
    pattern_group = prediction.get('pattern_group', 'Introductory Exploration')
    is_fallback = prediction.get('is_fallback', False)

    # Sort domain scores descending
    domain_scores = [(cat, features.get(cat, 0.0)) for cat in DOMAIN_CATEGORIES]
    domain_scores.sort(key=lambda x: x[1], reverse=True)

    top1_domain, top1_score = domain_scores[0]
    top2_domain, top2_score = domain_scores[1]
    min_domain, min_score = domain_scores[-1]

    # Handle cold start / introductory cases
    if is_fallback:
        if top1_score <= 0.0:
            observation = "Recent sessions show early exploration across introductory learning activities."
        else:
            observation = f"Recent sessions show emerging interaction in {DOMAIN_LABELS.get(top1_domain, top1_domain)} activities."
    else:
        # Normal clustered pattern
        score_gap = top1_score - min_score
        if score_gap <= 12.0:
            observation = "Recent sessions show balanced engagement and steady participation across learning activities."
        elif (top1_score - top2_score) >= 15.0:
            observation = f"Recent sessions show stronger engagement in {DOMAIN_LABELS.get(top1_domain, top1_domain)} activities."
        else:
            observation = f"Recent sessions show stronger engagement in {DOMAIN_LABELS.get(top1_domain, top1_domain)} and {DOMAIN_LABELS.get(top2_domain, top2_domain)} activities."

    return {
        'child_id': child_id,
        'pattern_group': pattern_group,
        'observation': observation,
        'features': features,
        'is_fallback': is_fallback,
        'cluster_id': prediction.get('cluster_id', -1)
    }
