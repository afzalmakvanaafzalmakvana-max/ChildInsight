import numpy as np
from sklearn.cluster import KMeans
from app.ml.features import FEATURE_NAMES

DEFAULT_RANDOM_STATE = 42

DISPLAY_NAMES = {
    'visual': 'Visual',
    'memory': 'Memory',
    'logic': 'Logic',
    'number': 'Number',
    'language': 'Language'
}


def generate_cluster_label_from_centroid(centroid):
    """Programmatically generates a descriptive, non-clinical pattern-group label from a 6D centroid vector."""
    # Centroid ordering: ['visual', 'memory', 'logic', 'number', 'language', 'engagement']
    domain_scores = {
        'Visual': float(centroid[0]),
        'Memory': float(centroid[1]),
        'Logic': float(centroid[2]),
        'Number': float(centroid[3]),
        'Language': float(centroid[4])
    }
    engagement = float(centroid[5]) if len(centroid) > 5 else 0.0

    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    top1_name, top1_score = sorted_domains[0]
    top2_name, top2_score = sorted_domains[1]
    min_name, min_score = sorted_domains[-1]

    score_spread = top1_score - min_score

    # Case 1: Relatively uniform distribution across domains
    if score_spread <= 12.0:
        if top1_score >= 70.0:
            label = "Balanced High-Engagement Interaction"
        elif top1_score <= 35.0:
            label = "Introductory Baseline Interaction"
        else:
            label = "Balanced Multi-Domain Interaction"
    # Case 2: One domain is distinctly prominent (at least 15 points higher than second)
    elif (top1_score - top2_score) >= 15.0:
        label = f"{top1_name} Focused Interaction"
    # Case 3: Two top domains show leading interaction
    else:
        label = f"{top1_name} + {top2_name} Strong Interaction"

    return {
        'label': label,
        'primary_domain': top1_name,
        'secondary_domain': top2_name,
        'top1_score': round(top1_score, 1),
        'top2_score': round(top2_score, 1),
        'engagement': round(engagement, 1),
        'domain_scores': {k: round(v, 1) for k, v in domain_scores.items()}
    }


def cluster_interaction_patterns(feature_matrix, n_clusters=3, random_state=DEFAULT_RANDOM_STATE):
    """Executes K-Means clustering over children's feature vectors and returns fitted models, centroids, and labels."""
    if len(feature_matrix) < n_clusters:
        raise ValueError(f"Insufficient samples ({len(feature_matrix)}) for {n_clusters} clusters.")

    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    cluster_assignments = kmeans.fit_predict(feature_matrix)

    cluster_meta = {}
    for idx, centroid in enumerate(kmeans.cluster_centers_):
        meta = generate_cluster_label_from_centroid(centroid)
        cluster_meta[idx] = {
            'cluster_id': idx,
            'label': meta['label'],
            'primary_domain': meta['primary_domain'],
            'secondary_domain': meta['secondary_domain'],
            'centroid': centroid.tolist(),
            'domain_scores': meta['domain_scores'],
            'engagement': meta['engagement']
        }

    return {
        'model': kmeans,
        'cluster_meta': cluster_meta,
        'cluster_assignments': cluster_assignments.tolist(),
        'n_clusters': n_clusters
    }
