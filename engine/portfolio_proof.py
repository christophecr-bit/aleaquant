"""Bounded joint conditional guarantees, attached to concrete portfolio content."""
from itertools import combinations, product
from math import comb

from portfolio_contract import resolve_pool, validate_grids, validate_profile
from portfolio_import import TOTAL, certify, content_hash, digest, require


def proof_for(grids, profile):
    validate_profile(profile)
    require(not validate_grids(grids, profile), 'preuve : grilles invalides ou hors contraintes du profil')
    nums, stars = resolve_pool(profile)
    requested = profile['constraints']['conditional_guarantee']
    hypothesis = requested or {'pool_good_numbers':5,'pool_good_stars':2,
                               'condition_mode':'exactly','required_numbers':0,
                               'required_stars':0,'threshold_mode':'at_least'}
    x,y = hypothesis['pool_good_numbers'],hypothesis['pool_good_stars']
    cases = comb(len(nums),x)*comb(50-len(nums),5-x)*comb(len(stars),y)*comb(12-len(stars),2-y)
    base = {'content_sha256':content_hash(grids),'pool_numbers':nums,'pool_stars':stars,
            'hypotheses':{'pool_good_numbers':x,'pool_good_stars':y,'condition_mode':'exactly'},
            'requested':requested,'threshold_mode':'at_least','cases':cases,
            'condition_probability':cases/TOTAL,'evaluator_version':'portfolio-proof-1.0'}
    limit = profile['evaluation']['max_certificate_cases']
    if cases > limit or cases*len(grids) > 2000000:
        return dict(base, method='not_checked', fulfilled=None,
                    condition='Condition exacte de pool ; enumeration au-delà des limites déclarées.',
                    reason='certificate_budget_exceeded')
    require(cases>0,'hypothèse conditionnelle sans issue')
    if x==5 and y==2:
        proof = dict(base, **{k:v for k,v in certify(grids,nums,stars,limit).items() if k not in base})
    else:
        outside_nums=sorted(set(range(1,51))-set(nums));outside_stars=sorted(set(range(1,13))-set(stars))
        minima={str(s):5 for s in range(3)}
        number_draws=[set(a+b) for a,b in product(combinations(nums,x),combinations(outside_nums,5-x))]
        star_draws=[set(a+b) for a,b in product(combinations(stars,y),combinations(outside_stars,2-y))]
        for dn,ds in product(number_draws,star_draws):
            hits=[(len(dn&set(g[0])),len(ds&set(g[1]))) for g in grids]
            for s in range(3):
                minima[str(s)]=min(minima[str(s)], max((n for n,st in hits if st>=s),default=-1))
        proof=dict(base,method='exhaustive_enumeration',verification='independent_recalculation',
                   minimum_best_numbers_by_required_stars=minima,
                   condition=f'Le pool contient exactement {x} des 5 numéros tirés et exactement {y} des 2 étoiles tirées ; seuils conjoints au moins R numéros et S étoiles sur une même grille.')
    proof['fulfilled']=(proof['minimum_best_numbers_by_required_stars'][str(requested['required_stars'])]>=requested['required_numbers']) if requested else True
    proof['id']='proof:'+digest(proof)
    return proof
