"""Audited graph construction and temporally separated participation mixing."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def section(out, table):
    out=Path(out);folder=out/'network_review'
    marker=folder/'manifest.json'
    if not marker.exists():
        return []
    manifest=json.loads(marker.read_text(encoding='utf-8'))
    for name,sha in manifest['outputs_sha256'].items():
        if hashlib.sha256((folder/name).read_text(encoding='utf-8').encode()).hexdigest()!=sha:
            raise ValueError('Network review checksum mismatch: '+name)
    audit=pd.read_csv(folder/'edge_audit.csv')
    cells=pd.read_csv(folder/'mixing_cells.csv')
    summary=pd.read_csv(folder/'mixing_summary.csv')
    exports=pd.read_csv(folder/'combined_exports.csv')
    main=summary[(summary.layer=='combined')&(summary.weighting=='reply_events')]
    pairs=list(main.pair.unique())
    groups=['a_only','b_only','both','unobserved']
    names={'superheroes':['Marvel only','DC only','Both','Unobserved'],
           'consoles':['PS5 only','Xbox only','Both','Unobserved']}
    fig,axes=plt.subplots(2,len(pairs),figsize=(6.5*len(pairs),10),squeeze=False)
    for col,pair in enumerate(pairs):
        for row,variant in enumerate(['all_replies','comment_replies']):
            ax=axes[row,col]
            data=cells[(cells.pair==pair)&(cells.variant==variant)&(cells.layer=='combined')&(cells.weighting=='reply_events')]
            matrix=data.pivot(index='origin_group',columns='destination_group',values='pct_origin').reindex(index=groups,columns=groups)
            ax.imshow(matrix,cmap='Blues',vmin=0,vmax=100)
            for i in range(4):
                for j in range(4):
                    value=matrix.iloc[i,j]
                    ax.text(j,i,f'{value:.1f}%',ha='center',va='center',color='white' if value>55 else '#18212b')
            labels=names.get(pair,groups)
            ax.set_xticks(range(4),labels,rotation=20,ha='right',fontsize=9)
            ax.set_yticks(range(4),labels,fontsize=9)
            ax.set_xlabel('Parent author: prior-window participation')
            ax.set_ylabel('Replier: prior-window participation')
            ax.set_title(f'{pair}: {variant.replace("_"," ")}\nSecond-window reply events; row percentages',fontsize=11)
    fig.tight_layout();fig.savefig(out/'figures/prior_participation_mixing.png',dpi=180);plt.close(fig)
    sections=['## Network construction audit and observed interaction across prior participation groups',
        f'All {len(audit)} original graphs were independently reconstructed from raw comment records using a '
        'parent-author join and grouped counts. Every saved directed edge, reply weight and node set matched. '
        'Where both comment records were available, the audit checked that the parent belongs to the same thread; top-level '
        'comments reference their thread post. This verifies consistency with the local archive records, '
        'not completeness or correctness of the archive itself.',
        table(audit[['window','subreddit','variant','edges','incorrect_or_missing_edges','extra_edges','node_set_difference']]),
        '### From membership overlap to observed replies',
        'Users are labelled from the first window only: A-only, B-only, both, or unobserved. These are participation '
        'categories, not fan allegiance, opinion or hostility. We then combine the two communities\' second-window '
        'reply graphs by merging identical account identifiers and summing only observed reply weights. Each edge '
        'retains its separate community-A/community-B reply counts. Shared membership creates no artificial edges. '
        'The same ordered dyad present in both layers is one combined dyad, with its reply events summed.',
        'A reply between prior A-only and prior B-only participants is direct observed interaction between those '
        'participation groups in the second window. It occurs inside a subreddit thread; it is not a comment '
        'physically replying across subreddits and does not establish information diffusion.',
        table(main[['pair','variant','total','known_prior_endpoint_pct','prior_exclusive_opposite_count',
                    'prior_exclusive_opposite_pct_all','categorical_assortativity_known']]),
        '![Prior participation mixing](outputs/study/figures/prior_participation_mixing.png)',
        'The matrix retains unobserved endpoints explicitly. Known-prior-endpoint coverage is the fraction of '
        'reply events for which both accounts were observed in the pair during the first window. The categorical '
        'assortativity coefficient is calculated only on that known subset: (observed same-group fraction minus '
        'the row/column marginal expectation) divided by (one minus that expectation). It is descriptive, with no '
        'null-model significance claim. It measures mixing by prior participation, not ideological homophily. '
        'Full matrices are also provided separately for each subreddit and for unweighted ordered dyads. '
        'Comment-only variants remove replies to original posts.',
        '### Separate subreddit layers versus their combination',
        table(summary[summary.weighting=='reply_events'][['pair','variant','layer','known_prior_endpoint_pct','categorical_assortativity_known']]),
        'A combined coefficient can be much larger than either layer coefficient because different prior groups '
        'participate in different subreddit layers. This aggregation effect means combined segregation cannot '
        'automatically be interpreted as selective avoidance of particular users inside a discussion space. '
        'All coefficients here use prior participation categories and omit unknown endpoints; they do not measure opinions.',
        '### Combined Gephi exports',
        table(exports),
        'Local files `outputs/study/networks/combined_*_full.gexf` preserve all observed nodes and edges. '
        'The focus files cap nodes by combined PageRank and retain the largest weak component of that cap; '
        'these are display-only selections. Node colors encode prior participation: blue A-only, orange B-only, '
        'green both, grey unobserved. Node size encodes incoming reply strength. Group labels and per-layer '
        'edge weights are available in the Gephi data table. No conclusion is drawn from layout distance.']
    validation=folder/'gephi_validation.csv'
    if validation.exists():
        checked=pd.read_csv(validation)
        sections += ['Native combined projects were saved and reopened by the official Gephi Toolkit, with '
            'node/edge/weight and directed-degree checks. Their ForceAtlas2 display further keeps repeated '
            'replies (weight at least two) and removes resulting isolates; full workspaces remain intact.',
            table(checked[['pair','variant','nodes','edges','degree_mismatches','project_reopened']])]
        for r in checked[checked.variant=='comment_replies'].itertuples():
            path=f'outputs/study/figures/gephi_combined_{r.pair}_{r.window}_{r.variant}.png'
            sections += [f'![Combined {r.pair} comment-reply network]({path})',
                f'*Prior-participation colors; ForceAtlas2 400 iterations, seed 42. Display: '
                f'{int(r.display_nodes):,} nodes/{int(r.display_edges):,} edges; full: '
                f'{int(r.nodes):,} nodes/{int(r.edges):,} edges. Layout is illustrative.*']
    return sections
