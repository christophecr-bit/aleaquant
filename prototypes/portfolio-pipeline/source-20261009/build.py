import numpy as np, itertools as it, math, json, random, time, pathlib, base64, html, argparse
ROOT=pathlib.Path(__file__).parent
parser=argparse.ArgumentParser()
parser.add_argument("--config",type=pathlib.Path,default=ROOT/"profiles.json")
parser.add_argument("--output",type=pathlib.Path,default=ROOT)
args=parser.parse_args()
cfg=json.loads(args.config.read_text())
ROOT=args.output;ROOT.mkdir(parents=True,exist_ok=True)
assert cfg["game"]=="euromillions" and cfg["unit_price_eur"]==2.5
assert cfg["evaluation"]["draws"]>=10000
assert len({x["id"] for x in cfg["profiles"]})==len(cfg["profiles"])
rng=random.Random(cfg["pool_seed"])
base=rng.sample(range(1,51),50); stars=rng.sample(range(1,13),12)
profiles=[]
def add(spec):
    id=spec["id"];family=spec["family"];c=spec["constraints"];m=c["grid_count"];v=c["pool_number_count"];s=c["pool_star_count"];w=spec["objectives"]
    assert family in ["Complete","Balanced","Spread","Clustered"]
    assert 5<=v<=50 and 2<=s<=12 and m>0 and m*2.5<=c["budget_max_eur"] and c["unique_grids"] is True
    assert m<=math.comb(v,5)*math.comb(s,2)
    if family=="Complete":assert m==math.comb(v,5)*math.comb(s,2)
    if family=="Clustered":assert m<=math.comb(v-3,2)*math.comb(s,2)
    assert spec["search"]["candidates_per_step"]>0
    pool=sorted(base[:v]); sp=sorted(stars[:s]); rr=random.Random(spec["search"]["seed"])
    if family=='Complete':
        grids=[(a,b) for a in it.combinations(pool,5) for b in it.combinations(sp,2)]
    else:
        grids=[]; freq={x:0 for x in pool}; sf={x:0 for x in sp}; seen_pairs=set(); seen_triples=set()
        for j in range(m):
            best=None; bs=-1e99
            for _ in range(spec["search"]["candidates_per_step"]):
                if family=='Clustered':
                    a=tuple(sorted(base[:3]+rr.sample(base[3:v],2)))
                else: a=tuple(sorted(rr.sample(pool,5)))
                b=tuple(sorted(rr.sample(sp,2)))
                if (a,b) in grids: continue
                pairs=set(it.combinations(a,2)); triples=set(it.combinations(a,3))
                ov=[len(set(a)&set(x)) for x,y in grids]
                score=w["maximize_distinct_triples"]*len(triples-seen_triples)+w["maximize_distinct_pairs"]*len(pairs-seen_pairs)-sum(freq[x] for x in a)*w["balance_number_frequency"]-sum(sf[x] for x in b)*w["balance_star_frequency"]-sum(o*o for o in ov)*w["minimize_overlap"]
                if score>bs: best=(a,b);bs=score
            if best is None:raise ValueError("Candidate search exhausted; increase candidates_per_step")
            grids.append(best);a,b=best
            for x in a:freq[x]+=1
            for x in b:sf[x]+=1
            seen_pairs.update(it.combinations(a,2));seen_triples.update(it.combinations(a,3))
    profiles.append(dict(id=id,family=family,profile_version=1,pool_numbers=pool,pool_stars=sp,budget_eur=m*2.5,
       constraints=dict(grid_count=m,unique_grids=True,number_range=[1,50],star_range=[1,12],numbers_per_grid=5,stars_per_grid=2),
       objectives=['maximize_distinct_triples','maximize_distinct_pairs','balance_frequencies','minimize_overlap'] if family in ['Balanced','Spread'] else ['complete_enumeration'] if family=='Complete' else ['shared_core','diversify_remaining_numbers'],
       generation=dict(method='enumeration' if family=='Complete' else 'greedy_candidate_search',candidates_per_step=spec["search"]["candidates_per_step"],seed=spec["search"]["seed"],pool_seed=cfg["pool_seed"]),
       lineage=dict(node_id=id,parent_ids=[],operation='initial_generation'),grids=[dict(numbers=list(a),stars=list(b)) for a,b in grids]))
for spec in cfg["profiles"]:add(spec)
for p in profiles:
    gs=p['grids'];m=len(gs)
    assert m==p['constraints']['grid_count'] and m*2.5==p['budget_eur']
    assert len({(tuple(g['numbers']),tuple(g['stars'])) for g in gs})==m
    for g in gs: assert len(set(g['numbers']))==5 and len(set(g['stars']))==2 and set(g['numbers'])<=set(p['pool_numbers']) and set(g['stars'])<=set(p['pool_stars'])
    overlaps=[len(set(a['numbers'])&set(b['numbers'])) for a,b in it.combinations(gs,2)]
    p['exact']={'mean_number_overlap':sum(overlaps)/len(overlaps),'max_number_overlap':max(overlaps),'distinct_pairs':len({x for g in gs for x in it.combinations(g['numbers'],2)}),'distinct_triples':len({x for g in gs for x in it.combinations(g['numbers'],3)}),'distinct_star_pairs':len({tuple(g['stars']) for g in gs}),'jackpot_probability':m/(math.comb(50,5)*66),'number_frequencies':{str(x):sum(x in g['numbers'] for g in gs) for x in p['pool_numbers']}}
    if len(p['pool_numbers'])<=15:
        # Complete enumeration of all 5+2 winning combinations inside the selected pools.
        ns=list(it.combinations(p['pool_numbers'],5));ss=list(it.combinations(p['pool_stars'],2))
        nc=np.array([[len(set(d)&set(g['numbers'])) for g in gs] for d in ns],dtype=np.int8)
        guaranteed={str(s):5 for s in range(3)}
        for d in ss:
            sc=np.array([len(set(d)&set(g['stars'])) for g in gs])
            for s in range(3):
                best=np.where(sc[None,:]>=s,nc,-1).max(axis=1)
                guaranteed[str(s)]=min(guaranteed[str(s)],int(best.min()))
        p['certificate']={'method':'exhaustive_enumeration','condition':'Les 5 numéros et les 2 étoiles tirés sont dans les pools indiqués.','cases':len(ns)*len(ss),'minimum_best_numbers_by_required_stars':guaranteed,'condition_probability':math.comb(len(p['pool_numbers']),5)/math.comb(50,5)*math.comb(len(p['pool_stars']),2)/66}
    else:p['certificate']={'method':'not_checked','condition':'Aucune garantie conditionnelle certifiée dans cette version.'}
print('Generation and exact checks complete',flush=True)
N=cfg["evaluation"]["draws"]; prng=np.random.default_rng(cfg["evaluation"]["seed"])
counts={p['id']:np.zeros(5,dtype=np.int64) for p in profiles}
for offset in range(0,N,10000):
    k=min(10000,N-offset)
    dn=np.argpartition(prng.random((k,50)),4,axis=1)[:,:5]+1
    ds=np.argpartition(prng.random((k,12)),1,axis=1)[:,:2]+1
    ni=np.zeros((k,51),np.int8);si=np.zeros((k,13),np.int8)
    ni[np.arange(k)[:,None],dn]=1;si[np.arange(k)[:,None],ds]=1
    for p in profiles:
        nh=np.stack([ni[:,g['numbers']].sum(axis=1) for g in p['grids']],axis=1)
        sh=np.stack([si[:,g['stars']].sum(axis=1) for g in p['grids']],axis=1)
        wins=((nh>=2)|((nh==1)&(sh==2))).sum(axis=1)
        counts[p['id']]+=np.array([(wins>=1).sum(),(wins>=2).sum(),(nh.max(axis=1)>=3).sum(),(nh.max(axis=1)>=4).sum(),wins.sum()])
def wilson(c):
    ph=c/N;z=1.95996398454;den=1+z*z/N
    mid=(ph+z*z/(2*N))/den;half=z*math.sqrt(ph*(1-ph)/N+z*z/(4*N*N))/den
    return [mid-half,mid+half]
for p in profiles:
    c=counts[p['id']];p['simulation']={'draws':N,'seed':cfg['evaluation']['seed'],'independent_of_generation':True,'same_draws_for_all':True,'metrics':{name:{'count':int(c[i]),'probability':float(c[i]/N),'ci95_wilson':wilson(c[i])} for i,name in enumerate(['any_prize','multiple_prizes','at_least_3_numbers','at_least_4_numbers'])},'mean_winning_grids':float(c[4]/N)}
    # Expected count of winning grids is independent of portfolio geometry; validate simulator within sampling tolerance.
    one=sum(math.comb(5,j)*math.comb(45,5-j)/math.comb(50,5) for j in range(2,6))+math.comb(5,1)*math.comb(45,4)/math.comb(50,5)/66
    p['simulation']['theoretical_mean_winning_grids']=len(p['grids'])*one
    # Mean count is reported as an analytical cross-check, not used for selection.
data={'config':cfg,'schema_version':'0.1','date':'2026-10-09','status':'prototype indépendant, non intégré au dépôt Aleaquant','price_eur':2.5,'exclusions':['Étoile+','My Million dans les probabilités (code non disponible avant validation)','montants de gain et probabilité de rembourser la mise'],'profiles':profiles}
(ROOT/'results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
atlas={'schema_version':'0.1','adapter_status':'proposed_contract_not_connected','nodes':[{'id':p['id'],'type':'portfolio','family':p['family'],'profile_version':p['profile_version'],'data':p} for p in profiles],'edges':[],'edge_types':['mutation_of','crossover_of','generated_from'],'note':'Initial population only; mutation and crossover execution are not implemented.'}
(ROOT/'atlas.json').write_text(json.dumps(atlas,ensure_ascii=False,indent=2))
print('Wrote results.json and atlas.json',flush=True)
