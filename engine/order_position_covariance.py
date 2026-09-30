"""Matrice théorique des numéros ordonnés d'un tirage uniforme k/N.

AleaQuant · 30/09/2026 · v0.1 (étude hors chaîne de publication).
Source : Coronel-Brizio et al., arXiv:0806.4595, équations 9–10.
Historique : première vérification déterministe du lien avec l'étendue.
TODO : qualifier l'estimation historique par régime avant toute entrée du registre.
"""
import argparse
from fractions import Fraction
import json

SUPPORTED_MAIN_REGIMES = {
    'euromillions': frozenset({(5, 50)}),
    'loto': frozenset({(6, 49), (5, 49)}),
    'keno': frozenset({(20, 70), (16, 56)}),
}


def theoretical_moments(picks: int, domain: int):
    """Retourne E[Y_i] et Cov(Y_i,Y_j) exactement, indices i,j de 1 à k."""
    if not 2 <= picks <= domain:
        raise ValueError('Il faut 2 <= picks <= domain')
    k, n = picks, domain
    mean = tuple(Fraction((n + 1) * i, k + 1) for i in range(1, k + 1))
    factor = Fraction((n + 1) * (n - k), (k + 1) ** 2 * (k + 2))
    covariance = tuple(tuple(
        min(i, j) * (k - max(i, j) + 1) * factor
        for j in range(1, k + 1)) for i in range(1, k + 1))
    return mean, covariance


def span_moments(mean, covariance):
    """E et Var de Y_k - Y_1 ; la covariance des extrêmes est indispensable."""
    if len(mean) < 2 or len(covariance) != len(mean):
        raise ValueError('Matrice incompatible avec le vecteur des moyennes')
    return (mean[-1] - mean[0],
            covariance[-1][-1] + covariance[0][0] - 2 * covariance[0][-1])


def report(game_id: str, picks: int, domain: int):
    if game_id not in SUPPORTED_MAIN_REGIMES:
        raise ValueError('Jeu inconnu : attendu euromillions, loto ou keno')
    if (picks, domain) not in SUPPORTED_MAIN_REGIMES[game_id]:
        raise ValueError(f'Régime principal non qualifié pour {game_id} : {picks}/{domain}')
    mean, covariance = theoretical_moments(picks, domain)
    span_mean, span_variance = span_moments(mean, covariance)
    return {
        'schema': 'aleaquant-order-position-theory-v1',
        'model': 'uniform k-subset without replacement',
        'game_id': game_id, 'component': 'main',
        'picks': picks, 'domain': domain,
        'source': 'https://arxiv.org/abs/0806.4595',
        'mean': [str(value) for value in mean],
        'covariance': [[str(value) for value in row] for row in covariance],
        'span_mean': str(span_mean),
        'span_variance': str(span_variance),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-id', required=True,
                        choices=('euromillions', 'loto', 'keno'))
    parser.add_argument('--picks', type=int, required=True)
    parser.add_argument('--domain', type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(report(args.game_id, args.picks, args.domain), ensure_ascii=False, indent=2))
