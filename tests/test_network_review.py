import networkx as nx
import pandas as pd
import pytest

from src.study_network_review import audit_graph, combine_layers, mixing, prior_groups, export_combined


def test_independent_edge_audit_detects_direction_and_weight_errors(monkeypatch):
    monkeypatch.setattr('src.study_network_review.anonymize',lambda name:name)
    raw = pd.DataFrame(dict(author=['a','a','b','c','d'],parent_id=['t1_b','t1_b','t3_p','t1_c','t1_missing']))
    parents={'t1_b':'b','t3_p':'p','t1_c':'c'}
    graph=nx.DiGraph()
    graph.add_nodes_from(['a','b','c','d','p'])
    graph.add_edge('a','b',weight=2);graph.add_edge('b','p',weight=1)
    result=audit_graph(graph,raw,parents)
    assert result['reply_events']==3 and result['missing_parent']==1 and result['self_replies_removed']==1
    with pytest.raises(AssertionError,match='reconstruction failed'):
        audit_graph(graph.reverse(),raw,parents)
    graph['a']['b']['weight']=1
    with pytest.raises(AssertionError,match='reconstruction failed'):
        audit_graph(graph,raw,parents)
    graph['a']['b']['weight']=2
    graph.remove_node('p')
    result=audit_graph(graph,raw,parents,comment_only=True)
    assert result['excluded_top_level']==1 and result['reply_events']==2


def test_layer_union_preserves_observed_edges_without_membership_edges():
    a,b=nx.DiGraph(),nx.DiGraph()
    a.add_nodes_from(['x','y','isolated'],observed_commenter=True)
    a.add_edge('x','y',weight=2)
    b.add_nodes_from(['x','z'],observed_commenter=True)
    b.add_node('y',observed_commenter=False)
    b.add_edge('x','y',weight=3);b.add_edge('z','x',weight=1)
    graph=combine_layers([a,b],{'x':'both','y':'a_only'})
    assert len(graph)==4 and graph.number_of_edges()==2
    assert graph['x']['y']==dict(weight=5,weight_a=2,weight_b=3)
    assert graph.nodes['x']['current_group']=='both'
    assert graph.nodes['y']['current_group']=='a_only'
    assert graph.nodes['z']['prior_group']=='unobserved'
    assert graph.degree('isolated')==0


def test_weighted_directed_mixing_retains_unknowns_and_uses_endpoint_marginals():
    graph=nx.DiGraph()
    graph.add_weighted_edges_from([('a','a2',2),('a','b',1),('b','a',1),('b','b2',2),('u','a',4)])
    groups={'a':'a_only','a2':'a_only','b':'b_only','b2':'b_only'}
    cells,summary=mixing(graph,groups)
    assert sum(r['count'] for r in cells)==10
    assert summary['known_prior_endpoint_pct']==60
    assert summary['prior_exclusive_opposite_pct_all']==20
    assert summary['categorical_assortativity_known']==pytest.approx(1/3)
    _,unweighted=mixing(graph,groups,False)
    assert unweighted['total']==5 and unweighted['categorical_assortativity_known']==0


def test_prior_labels_use_only_supplied_period_and_export_roundtrips(tmp_path,monkeypatch):
    monkeypatch.setattr('src.study_network_review.anonymize',lambda name:name)
    raw=pd.DataFrame(dict(author=['x','x','y'],subreddit=['A','B','B']))
    labels=prior_groups(raw,{'communities':['A','B']})
    assert labels=={'x':'both','y':'b_only'}
    graph=nx.DiGraph()
    graph.add_edge('x','y',weight=2)
    graph=combine_layers([graph,nx.DiGraph()],labels)
    meta=export_combined(graph,tmp_path,'example',dict(seed=42,display_limit=10))
    loaded=nx.read_gexf(tmp_path/'example_full.gexf')
    assert loaded['x']['y']['weight_a']==2 and loaded.nodes['x']['prior_group']=='both'
    assert meta['full_reply_events']==2 and meta['display_nodes']==2
