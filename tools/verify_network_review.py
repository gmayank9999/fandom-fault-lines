"""Public aggregate integrity checks for the independent network review."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    out=Path('outputs/study'); folder=out/'network_review'
    manifest=json.loads((folder/'manifest.json').read_text())
    assert manifest['source_sha256']==hashlib.sha256(Path('src/study_network_review.py').read_text(encoding='utf-8').encode()).hexdigest()
    for name,sha in manifest['outputs_sha256'].items():
        assert sha==hashlib.sha256((folder/name).read_text(encoding='utf-8').encode()).hexdigest(),name
    audit=pd.read_csv(folder/'edge_audit.csv')
    matrices=pd.read_csv(folder/'mixing_cells.csv')
    summary=pd.read_csv(folder/'mixing_summary.csv')
    exports=pd.read_csv(folder/'combined_exports.csv')
    assert (len(audit),len(matrices),len(summary),len(exports))==(16,384,24,4)
    assert audit.exact_reconstruction.all()
    assert (audit[['incorrect_or_missing_edges','extra_edges','node_set_difference','parent_thread_mismatches']]==0).all().all()
    assert (audit.participation_comments==audit[['reply_events','missing_parent','self_replies_removed','excluded_top_level']].sum(axis=1)).all()
    keys=['pair','window','variant','layer','weighting']
    for key,group in matrices.groupby(keys):
        matching=summary
        for col,value in zip(keys,key):
            matching=matching[matching[col]==value]
        r=matching.iloc[0]
        assert np.isclose(group['count'].sum(),r.total)
        known=group[(group.origin_group!='unobserved')&(group.destination_group!='unobserved')]
        assert np.isclose(known['count'].sum(),r.known_prior_endpoints)
        assert np.isclose(known[known.origin_group!=known.destination_group]['count'].sum()+known[known.origin_group==known.destination_group]['count'].sum(),r.known_prior_endpoints)
        positive=group.groupby('origin_group')['count'].sum()>0
        assert np.allclose(group.groupby('origin_group').pct_origin.sum()[positive],100)
    for r in exports.itertuples():
        original=audit[(audit.pair==r.pair)&(audit.window==r.window)&(audit.variant==r.variant)]
        assert r.full_reply_events==original.reply_events.sum()
        assert r.full_edges<=original.edges.sum()
        assert original.nodes.max()<=r.full_nodes<=original.nodes.sum()
        assert r.display_nodes<=r.full_nodes and r.display_edges<=r.full_edges
    validation=folder/'gephi_validation.csv'
    if validation.exists():
        gephi=pd.read_csv(validation)
        assert len(gephi)==4 and gephi.project_reopened.all() and (gephi.degree_mismatches==0).all()
        merged=exports.merge(gephi,on=['pair','window','variant'])
        assert len(merged)==4 and (merged.full_nodes==merged.nodes).all() and (merged.full_edges==merged.edges).all()
        assert (merged.full_reply_events==merged.reply_weight).all()
    print('PASS: 16 exact graph audits, 384 directed mixing cells, 24 layer/weight comparisons, four combined graphs.')


if __name__=='__main__':
    main()
