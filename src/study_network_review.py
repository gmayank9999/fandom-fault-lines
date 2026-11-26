"""Independent raw-edge audit and prior-participation mixing across reply layers."""
import hashlib
import json
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from src.study_analysis import valid_users
from src.study_data import load_window, raw_parent_lookup, read_design
from src.utils import anonymize

GROUPS = ['a_only', 'b_only', 'both', 'unobserved']
COLORS = [(37,99,166), (195,91,38), (35,132,109), (160,160,160)]


def independent_edges(comments, parent_authors, comment_only=False):
    """DataFrame join/groupby reconstruction, independent of the graph builder."""
    eligible = comments if not comment_only else comments[comments.parent_id.str.startswith('t1_', na=False)]
    resolved = eligible.assign(parent_author=eligible.parent_id.map(parent_authors))
    missing = resolved.parent_author.isna()
    same = (~missing) & resolved.author.eq(resolved.parent_author)
    usable = resolved[~missing & ~same]
    counts = usable.groupby(['author', 'parent_author']).size()
    hashed = {name: anonymize(name) for name in set(comments.author) | set(usable.parent_author)}
    expected = {(hashed[a], hashed[b]): int(n) for (a, b), n in counts.items()}
    nodes = {hashed[a] for a in comments.author} | {hashed[a] for a in usable.parent_author}
    return expected, nodes, dict(participation_comments=len(comments), eligible_comments=len(eligible),
        missing_parent=int(missing.sum()), self_replies_removed=int(same.sum()),
        excluded_top_level=len(comments)-len(eligible), reply_events=len(usable))


def audit_graph(graph, comments, parent_authors, comment_only=False):
    expected, nodes, events = independent_edges(comments, parent_authors, comment_only)
    actual = {(a,b): d['weight'] for a,b,d in graph.edges(data=True)}
    wrong = sum(actual.get(edge) != count for edge,count in expected.items())
    extra = len(set(actual)-set(expected))
    difference = len(set(graph) ^ nodes)
    assert graph.is_directed() and not graph.is_multigraph()
    assert not wrong and not extra and not difference, f'Raw-edge reconstruction failed: {wrong}, {extra}, {difference}'
    assert not nx.number_of_selfloops(graph)
    assert events['participation_comments'] == sum(events[k] for k in ['missing_parent','self_replies_removed','excluded_top_level','reply_events'])
    return dict(**events, nodes=len(graph), edges=len(actual), incorrect_or_missing_edges=wrong,
        extra_edges=extra, node_set_difference=difference, exact_reconstruction=True)


def prior_groups(first_window, pair):
    sets = [set(first_window.loc[first_window.subreddit == sub, 'author'].map(anonymize)) for sub in pair['communities']]
    return {u: ('both' if u in sets[0] and u in sets[1] else 'a_only' if u in sets[0] else 'b_only')
            for u in sets[0] | sets[1]}


def combine_layers(graphs, groups):
    combined = nx.DiGraph()
    for layer, graph in enumerate(graphs):
        for node in graph:
            if node not in combined:
                combined.add_node(node, prior_group=groups.get(node, 'unobserved'),
                    observed_a=False, observed_b=False)
            observed = str(graph.nodes[node].get('observed_commenter', False)).lower() == 'true'
            combined.nodes[node]['observed_a' if layer == 0 else 'observed_b'] = observed
        for a,b,attrs in graph.edges(data=True):
            if not combined.has_edge(a,b):
                combined.add_edge(a,b,weight=0,weight_a=0,weight_b=0)
            combined[a][b]['weight'] += int(attrs['weight'])
            combined[a][b]['weight_a' if layer == 0 else 'weight_b'] += int(attrs['weight'])
    for node, attrs in combined.nodes(data=True):
        a,b = attrs['observed_a'], attrs['observed_b']
        attrs['current_group'] = 'both' if a and b else 'a_only' if a else 'b_only' if b else 'parent_only'
        attrs['in_strength'] = float(combined.in_degree(node, weight='weight'))
    assert combined.size(weight='weight') == sum(g.size(weight='weight') for g in graphs)
    return combined


def mixing(graph, groups, weighted=True):
    matrix = np.zeros((4,4))
    mapping = {g:i for i,g in enumerate(GROUPS)}
    for a,b,attrs in graph.edges(data=True):
        matrix[mapping[groups.get(a,'unobserved')], mapping[groups.get(b,'unobserved')]] += attrs['weight'] if weighted else 1
    total = matrix.sum()
    known = matrix[:3,:3]
    known_total = known.sum()
    same = float(np.trace(known)/known_total) if known_total else np.nan
    if known_total:
        frequencies = known/known_total
        expectation = float(np.dot(frequencies.sum(axis=1), frequencies.sum(axis=0)))
        assortativity = (same-expectation)/(1-expectation) if expectation < 1-1e-12 else np.nan
    else:
        expectation, assortativity = np.nan,np.nan
    opposite = float(matrix[0,1]+matrix[1,0])
    rows = [dict(origin_group=a, destination_group=b, count=float(matrix[i,j]),
        pct_all=100*matrix[i,j]/total if total else np.nan,
        pct_origin=100*matrix[i,j]/matrix[i].sum() if matrix[i].sum() else np.nan)
        for i,a in enumerate(GROUPS) for j,b in enumerate(GROUPS)]
    return rows, dict(total=total, known_prior_endpoints=known_total,
        known_prior_endpoint_pct=100*known_total/total if total else np.nan,
        prior_exclusive_opposite_count=opposite,
        prior_exclusive_opposite_pct_all=100*opposite/total if total else np.nan,
        prior_exclusive_opposite_pct_known=100*opposite/known_total if known_total else np.nan,
        same_prior_group_pct_known=100*same, marginal_expected_same_pct_known=100*expectation,
        categorical_assortativity_known=assortativity)


def export_combined(graph, folder, stem, settings):
    rank = nx.pagerank(graph, weight='weight', tol=1e-10, max_iter=500)
    for node in graph:
        graph.nodes[node].update(in_degree=graph.in_degree(node), out_degree=graph.out_degree(node),
                                 pagerank=float(rank[node]))
    nx.write_gexf(graph, folder / f'{stem}_full.gexf')
    keep = sorted(graph, key=lambda u:(-rank[u],u))[:settings['display_limit']]
    focus = graph.subgraph(keep).copy()
    # A display only: preserve the largest weak component of the capped graph.
    if len(focus):
        focus = focus.subgraph(max(nx.weakly_connected_components(focus), key=len)).copy()
    layout_graph = nx.Graph()
    for a,b,d in focus.edges(data=True):
        weight = layout_graph[a][b]['weight'] if layout_graph.has_edge(a,b) else 0
        layout_graph.add_edge(a,b,weight=weight+d['weight'])
    layout_graph.add_nodes_from(focus)
    positions = nx.spring_layout(layout_graph, seed=settings['seed'], iterations=50)
    for node in focus:
        x,y = positions[node]
        r,g,b = COLORS[GROUPS.index(focus.nodes[node]['prior_group'])]
        focus.nodes[node]['pagerank_combined'] = float(rank[node])
        focus.nodes[node]['viz'] = dict(color=dict(r=r,g=g,b=b,a=1.),
            position=dict(x=float(x)*1000,y=float(y)*1000,z=0.),
            size=float(2+np.log1p(focus.nodes[node]['in_strength'])))
    nx.write_gexf(focus, folder / f'{stem}_focus.gexf')
    return dict(full_nodes=len(graph), full_edges=graph.number_of_edges(),
        full_reply_events=int(graph.size(weight='weight')), display_nodes=len(focus),display_edges=focus.number_of_edges())


def run(design, settings):
    windows = sorted(design['windows'],key=lambda w:w['start'])
    if len(windows) != 2:
        raise ValueError('Review needs two ordered observation windows')
    out = Path(design['output_dir'])
    folder = out/'network_review'; folder.mkdir(parents=True,exist_ok=True)
    (folder/'manifest.json').unlink(missing_ok=True)
    parents = valid_users(raw_parent_lookup())
    audits, matrices, summaries, exports = [],[],[],[]
    inputs = {}
    for pair in design['pairs']:
        print('NETWORK REVIEW', pair['id'], flush=True)
        raw = pd.concat([load_window(w,pair['communities']).assign(window=w['id']) for w in windows], ignore_index=True)
        clean = valid_users(raw)
        parent_authors = dict(zip('t1_'+clean.id,clean.author))
        parent_authors.update(dict(zip(parents.kind+'_'+parents.id,parents.author)))
        # Validate parent-link relationships where both comment records are observed.
        known_threads = dict(zip('t1_'+raw.id,raw.link_id))
        parent_thread = raw.parent_id.map(known_threads)
        wrong_thread = parent_thread.notna() & parent_thread.ne(raw.link_id)
        top_mismatch = raw.parent_id.str.startswith('t3_',na=False) & raw.parent_id.ne(raw.link_id)
        if wrong_thread.any() or top_mismatch.any():
            raise ValueError('Observed parent/thread inconsistency; inspect raw records before continuing')
        groups = prior_groups(clean[clean.window == windows[0]['id']], pair)
        inputs[pair['id']+'_raw_records'] = hashlib.sha256(raw.to_csv(index=False).encode()).hexdigest()
        for w in windows:
            for variant in settings['variants']:
                graphs=[]
                for sub in pair['communities']:
                    path = out/'networks'/f"{pair['id']}_{w['id']}_{sub}_{variant}_full.gexf"
                    graph = nx.read_gexf(path)
                    inputs[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                    comments = clean[(clean.window == w['id']) & (clean.subreddit == sub)]
                    result = audit_graph(graph,comments,parent_authors,variant=='comment_replies')
                    audits.append(dict(pair=pair['id'],window=w['id'],subreddit=sub,variant=variant,
                        parent_thread_mismatches=0,**result))
                    print('VERIFIED',w['id'],sub,variant,flush=True)
                    graphs.append(graph)
                if w != windows[1]:
                    continue
                combined = combine_layers(graphs,groups)
                for layer, graph in list(zip(pair['communities'],graphs))+[('combined',combined)]:
                    for weighting in ['reply_events','ordered_dyads']:
                        rows,summary = mixing(graph,groups,weighting=='reply_events')
                        base=dict(pair=pair['id'],window=w['id'],variant=variant,layer=layer,weighting=weighting)
                        matrices.extend(dict(**base,**r) for r in rows)
                        summaries.append(dict(**base,**summary))
                stem = f"combined_{pair['id']}_{w['id']}_{variant}"
                metadata = export_combined(combined,out/'networks',stem,settings)
                exports.append(dict(pair=pair['id'],window=w['id'],variant=variant,**metadata))
    for name,rows in [('edge_audit',audits),('mixing_cells',matrices),('mixing_summary',summaries),('combined_exports',exports)]:
        pd.DataFrame(rows).to_csv(folder/f'{name}.csv',index=False)
    manifest=dict(settings=settings,inputs_sha256=inputs,
        source_sha256=hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),
        outputs_sha256={name+'.csv':hashlib.sha256((folder/(name+'.csv')).read_text(encoding='utf-8').encode()).hexdigest()
                        for name in ['edge_audit','mixing_cells','mixing_summary','combined_exports']})
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('COMPLETE network review',flush=True)


if __name__ == '__main__':
    run(read_design(),json.loads(Path('network_review.json').read_text()))
