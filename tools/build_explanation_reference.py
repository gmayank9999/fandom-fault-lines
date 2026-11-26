"""Refresh the final guide's reference appendix from local, public study evidence.

The explanatory chapters before the marker remain hand-maintained. This does not
collect data, recompute research results or read private text/account tables.
"""
import ast
import csv
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'explanation_final.md'
MARKER = '<!-- GENERATED_REFERENCE_START -->'
parts = []


def emit(value=''):
    parts.append(value + '\n')


def rows(path):
    with (ROOT / path).open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def cell(value):
    if value is None or value == '':
        return '—'
    text = str(value)
    try:
        if text not in ('True', 'False'):
            n = float(text)
            if n == int(n):
                text = f'{int(n):,}'
            elif 0 < abs(n) < .001:
                text = f'{n:.3g}'
            else:
                text = f'{n:.4f}'.rstrip('0').rstrip('.')
    except (ValueError, OverflowError):
        pass
    return text.replace('|', '\\|').replace('\n', ' ')


def table(title, data, columns, sources, intro=''):
    emit('### ' + title)
    if intro:
        emit(intro + '\n')
    emit('Source: ' + ', '.join(f'[{Path(p).name}]({p})' for p in sources) + '.\n')
    emit('| ' + ' | '.join(columns) + ' |')
    emit('| ' + ' | '.join('---' for _ in columns) + ' |')
    for row in data:
        emit('| ' + ' | '.join(cell(row[c]) for c in columns) + ' |')
    emit()


def pair_tables(suffix):
    paths = [f'outputs/study/tables/{pair}_{suffix}.csv' for pair in ('superheroes', 'consoles')]
    return [r for p in paths for r in rows(p)], paths


def main():
    source = DOC.read_text(encoding='utf-8')
    assert source.count(MARKER) == 1
    paths = ['outputs/study/collection_inventory.csv']
    table('27.1 Collection by community and window', rows(paths[0]),
          ['window', 'subreddit', 'expected_days', 'valid_days', 'rows', 'manifest_days', 'complete_files'], paths,
          'Manifest days count files with a checked request manifest. Zero does not mean zero comments; it identifies inherited provenance limits.')
    data, paths = pair_tables('corpus')
    table('27.2 Raw, participation and content populations', data,
          ['window', 'subreddit', 'raw_comments', 'participation_comments', 'content_comments', 'commenters', 'content_commenters', 'rival_mention_pct', 'shared_users_comment_share_pct'], paths,
          'The last column is the percentage of participation comments written by shared accounts, not the percentage of accounts that are shared.')
    data, paths = pair_tables('overlap')
    table('27.3 All pair-window overlap thresholds', data,
          ['pair', 'window', 'min_comments', 'users_a', 'users_b', 'shared', 'pct_a', 'pct_b', 'jaccard_pct'], paths)
    path = 'outputs/study/tables/all_pair_overlap.csv'
    table('27.4 All 15 audience pairs in both windows', [r for r in rows(path) if r['min_comments'] == '1'],
          ['window', 'community_a', 'community_b', 'shared', 'pct_smaller', 'jaccard_pct'], [path],
          'Threshold one. `pct_smaller` divides by the smaller audience. Thresholds two and five remain in the source table and its inventory below.')
    data, paths = pair_tables('duration')
    table('27.5 Cumulative duration sensitivity', data, ['pair', 'window', 'days', 'users_a', 'users_b', 'shared', 'jaccard_pct'], paths)
    data, paths = pair_tables('sampling')
    grouped = {}
    for row in data:
        key = row['pair'], row['window'], row['fraction']
        grouped.setdefault(key, []).append(float(row['jaccard_pct']))
    summary = [dict(pair=k[0], window=k[1], fraction=k[2], replicates=len(v), mean_jaccard_pct=sum(v)/len(v),
                    min_jaccard_pct=min(v), max_jaccard_pct=max(v)) for k,v in grouped.items()]
    table('27.6 Sampling means and ranges', summary,
          ['pair', 'window', 'fraction', 'replicates', 'mean_jaccard_pct', 'min_jaccard_pct', 'max_jaccard_pct'], paths,
          'Computed directly from the saved replicate rows. These ranges describe five random subsamples where applicable; they are not confidence intervals.')
    data, paths = pair_tables('networks')
    table('27.7 All 16 original graph sizes and connectivity', data,
          ['window', 'subreddit', 'variant', 'nodes', 'edges', 'reply_events', 'isolates', 'largest_component_pct', 'reciprocity'], paths)
    table('27.8 Parent coverage and event accounting', data,
          ['window', 'subreddit', 'variant', 'eligible_comments', 'missing_parent', 'resolved_parent_pct', 'self_replies_removed', 'excluded_top_level'], paths)
    table('27.9 Original all-reply modularity and approximation diagnostics', [r for r in data if r['variant']=='all_replies'],
          ['window', 'subreddit', 'modularity_weighted', 'modularity_unweighted', 'null_mean', 'null_sd', 'modularity_excess', 'top20_betweenness_seed_overlap'], paths,
          'The null comparison concerns unweighted topology. Seed overlap compares approximate top-20 node sets; it is not audience overlap.')
    data, paths = pair_tables('sentiment')
    table('27.10 All mention-category sentiment summaries', data,
          ['window', 'subreddit', 'target', 'n', 'mean_vader', 'mean_vader_adapted', 'zero_vader_pct'], paths,
          'Mean scores range from −1 to +1. A zero score is a lexical scoring result, not human proof of neutrality.')
    data, paths = pair_tables('tests')
    table('27.11 Main adapted-VADER any-rival comparisons', [r for r in data if r['scorer']=='vader_adapted' and r['contrast']=='any_rival_mention'],
          ['window', 'subreddit', 'n_a', 'n_b', 'author_diff', 'effect_size_r', 'author_p_boot_holm', 'link_id_p_boot_holm', 'supported_both_clusterings'], paths,
          'A is own-only and B is any rival mention. The full tables additionally retain the original scorer, rival-only contrasts and interval endpoints.')
    data, paths = pair_tables('topic_selection')
    # Pair is implied by separate selection files, so attach it explicitly.
    data = [dict(pair=Path(p).name.split('_')[0], **r) for p in paths for r in rows(p)]
    table('27.12 All candidate topic models', data, ['pair', 'k', 'npmi', 'selected', 'training_comments'], paths)
    data, paths = pair_tables('topics')
    unique = {}
    for p in paths:
        pair = Path(p).name.split('_')[0]
        for row in rows(p):
            unique[pair,row['topic']] = dict(pair=pair,topic=row['topic'],words=row['words'])
    table('27.13 Every selected topic and its keywords', list(unique.values()), ['pair','topic','words'], paths,
          'The keywords are the saved model output. They are not manual labels. Topic −1 is an explicit unassigned category.')
    table('27.14 Topic assignment coverage', [dict(pair=Path(p).name.split('_')[0],**r) for p in paths for r in rows(p) if r['topic']=='-1'],
          ['pair','window','subreddit','comments','share_pct'], paths, 'These rows count unassigned comments and their percentage of all usable content.')
    path='outputs/study/advanced/transitions.csv'
    table('27.15 Complete threshold-one participation transitions', [r for r in rows(path) if r['min_comments']=='1'],
          ['pair','origin_state','destination_state','users','origin_users','origin_pct'], [path])
    path='outputs/study/advanced/persistence.csv'
    table('27.16 Persistence at every activity threshold', rows(path),
          ['pair','min_comments','pattern','users','pooled_shared_users','pct_pooled_shared'], [path])
    path='outputs/study/advanced/retention.csv'
    table('27.17 Return estimates for both outcomes', rows(path),
          ['pair','reference','outcome','raw_both_pct','raw_exclusive_pct','adjusted_both_pct','adjusted_exclusive_pct','adjusted_difference_pp','ci_low_pp','ci_high_pp'], [path])
    table('27.18 Return comparison populations', [r for r in rows(path) if r['outcome']=='observed_in_pair'],
          ['pair','reference','both_users','exclusive_users','common_both_users','common_exclusive_users'], [path],
          'Excluded accounts can be obtained by subtracting common-support counts from the corresponding total. Comparison populations differ.')
    path='outputs/study/advanced/paired_sentiment.csv'
    table('27.19 All 64 paired-author sensitivity comparisons', rows(path),
          ['window','subreddit','scorer','contrast','min_per_category','paired_authors','author_equal_weight_difference','ci_low','ci_high'], [path],
          'Unadjusted descriptive intervals. These rows should not be relabeled as 64 corrected significance tests.')
    path='outputs/study/advanced/matched_connectors.csv'
    table('27.20 All 32 matched connector comparisons', rows(path),
          ['window','subreddit','variant','matching','selected_users','observed_shared_pct','matched_expected_shared_pct','excess_pp','enrichment_p','enrichment_p_holm'], [path])
    path='outputs/study/network_review/edge_audit.csv'
    table('27.21 Independent reconstruction of every original graph', rows(path),
          ['window','subreddit','variant','edges','incorrect_or_missing_edges','extra_edges','node_set_difference','parent_thread_mismatches','exact_reconstruction'], [path])
    path='outputs/study/network_review/mixing_summary.csv'
    table('27.22 All layer/weighting mixing summaries', rows(path),
          ['pair','variant','layer','weighting','total','known_prior_endpoint_pct','prior_exclusive_opposite_count','categorical_assortativity_known'], [path],
          'The total is reply events or ordered dyads according to `weighting`. Opposite-exclusive counts sum the A-only-to-B-only and B-only-to-A-only cells.')
    path='outputs/study/network_review/mixing_cells.csv'
    table('27.23 Complete combined reply-event mixing cells', [r for r in rows(path) if r['layer']=='combined' and r['weighting']=='reply_events'],
          ['pair','variant','origin_group','destination_group','count','pct_all','pct_origin'], [path],
          'Includes unknown prior endpoints. The source also includes separate-layer and ordered-dyad matrices.')
    paths=['outputs/study/gephi_validation.csv','outputs/study/network_review/gephi_validation.csv']
    data=[dict(project=r.get('subreddit',r.get('variant')),**r) for p in paths for r in rows(p)]
    table('27.24 All 12 native Gephi validations and final display sizes',data,
          ['pair','window','project','nodes','edges','reply_weight','degree_mismatches','pagerank_l1_difference_python','project_reopened','display_nodes','display_edges'],paths)

    emit('## 28. Complete aggregate CSV inventory\n')
    emit('This inventory includes every CSV directly under `outputs/study/` and its public `tables`, `advanced` and `network_review` folders. It intentionally does not enumerate private text/account rows or the hundreds of daily raw files. Columns are listed in stored order; their analytical meanings are explained in Sections 6–23. Row counts exclude the header.\n')
    files=sorted(set((ROOT/'outputs/study').glob('*.csv')) | set((ROOT/'outputs/study/tables').glob('*.csv')) |
                 set((ROOT/'outputs/study/advanced').glob('*.csv')) | set((ROOT/'outputs/study/network_review').glob('*.csv')))
    for p in files:
        rel=p.relative_to(ROOT).as_posix()
        with p.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.reader(f); header=next(reader); count=sum(1 for _ in reader)
        emit(f'### `{rel}`\n')
        emit(f'[{p.name}]({rel}) — **{count:,} rows; {len(header)} columns**.\n')
        emit('Columns: '+', '.join(f'`{c}`' for c in header)+'.\n')

    emit('## 29. Exact configuration and implementation excerpts\n')
    emit('These excerpts are copied from the current files, not rewritten pseudocode. The long configuration listings make the exact dates, dictionaries, seeds and thresholds available inside this guide. JSON stores names and values; square brackets contain lists and braces contain objects.\n')
    for path in ['study.json','advanced_study.json','network_review.json']:
        emit(f'### {path}\n\nSource: [{path}]({path}).\n')
        emit('```json\n'+json.dumps(json.loads((ROOT/path).read_text(encoding='utf-8')),indent=2,ensure_ascii=False)+'\n```\n')
    excerpts=[
        ('src/preprocess.py','clean_text','Cleaning text','Regular-expression substitutions remove markup and URLs, then collapse whitespace. The function returns cleaned text; `basic_clean()` applies the account/body/length/letter filters explained earlier.'),
        ('src/study_analysis.py','overlap_counts','Calculating overlap','Counts at or above the chosen threshold become sets. `&` computes intersection, `|` union, and `len()` counts distinct elements. Every percentage has an explicit denominator.'),
        ('src/study_network.py','graph_from_comments','Building the directed weighted graph','Nodes are added before edges, preserving isolates. `continue` skips an excluded event. Existing ordered edges increment their weight. The returned dictionary records the accounting categories.'),
        ('src/network_analysis.py','undirected_sum','Summing reciprocal weights','The loop visits every directed edge and accumulates its weight into an undirected pair, so opposite directions both contribute.'),
        ('src/study_advanced.py','state','Assigning participation states','`>= threshold` creates true/false comparisons. `np.select` assigns both first, then exclusive states, otherwise neither. The `window` argument selects the relevant period counts.'),
        ('src/study_network_review.py','mixing','Computing directed group mixing','The 4×4 matrix retains unknown endpoints. The first three groups form the known subset used for the coefficient. Row and column marginals determine the expected same-group fraction.')]
    for path,name,title,explanation in excerpts:
        code=(ROOT/path).read_text(encoding='utf-8'); tree=ast.parse(code)
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
        snippet='\n'.join(code.splitlines()[function.lineno-1:function.end_lineno])
        emit(f'### {title}\n\n{explanation}\n\nSource: [{path}]({path}).\n\n```python\n{snippet}\n```\n')
    emit('### Reading a result without rerunning the study\n')
    emit('The following example only reads existing aggregate CSVs. A DataFrame is a table in pandas. Boolean conditions select the rows of interest; the final print displays selected columns.\n')
    emit('```python\nimport pandas as pd\n\nnetwork = pd.read_csv("outputs/study/tables/consoles_networks.csv")\nxbox_sep = network[(network["subreddit"] == "xbox") & (network["window"] == "sep")]\nprint(xbox_sep[["variant", "nodes", "edges", "largest_component_pct"]].to_string(index=False))\n\noverlap = pd.read_csv("outputs/study/tables/superheroes_overlap.csv")\npooled = overlap[(overlap["window"] == "pooled_56d") & (overlap["min_comments"] == 1)]\nprint(pooled[["shared", "pct_a", "pct_b", "jaccard_pct"]].to_string(index=False))\n```\n')
    emit('### Additional shared settings\n')
    config_tree=ast.parse((ROOT/'config.py').read_text(encoding='utf-8'))
    for name in ['BOT_ACCOUNTS','DOMAIN_NEUTRAL_WORDS','MIN_COMMENT_LENGTH','TOPIC_MIN_TOKENS']:
        node=next(n for n in config_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
        value=ast.literal_eval(node.value)
        if isinstance(value,set): value=sorted(value)
        emit(f'**`{name}`:** '+json.dumps(value,ensure_ascii=False)+'.\n')
    emit('The first list is account filtering, the second is the adapted-VADER lexicon removal list. The numeric thresholds apply to cleaned-character length and nonzero topic features respectively.\n')
    emit('### Reference integrity\n')
    emit('The appendix was assembled by `tools/build_explanation_reference.py`. The explanatory chapters before its marker are maintained separately. The evidence digest below hashes the sorted public CSV paths and their exact bytes for this snapshot; it is an audit fingerprint, not a scientific statistic.\n')
    h=hashlib.sha256()
    for p in files:
        h.update(p.relative_to(ROOT).as_posix().encode());h.update(p.read_bytes())
    emit(f'Public CSV evidence SHA-256: `{h.hexdigest()}`.\n')
    emit('## 30. Literature and methodological references\n')
    emit('This bibliography is retained from the course report. It records the sources used in the project write-up, rather than claiming a new exhaustive literature search for this guide. Political-discussion findings in these papers motivate measurement choices; they are not direct evidence that entertainment fandoms behave identically.\n')
    emit('The design draws on distinctions between interaction and participation boundaries, explicit Reddit thread mechanics, careful interpretation of Louvain groups, temporal ordering, activity concentration, and validated target-specific stance. These connections explain why we added reply-definition sensitivities, equal-author comparisons, matched connectors and a human annotation protocol.\n')
    report=(ROOT/'reports/course_report.html').read_text(encoding='utf-8')
    refs=re.findall(r'<p class="reference">(.*?)</p>',report,re.S)
    for ref in refs:
        ref=re.sub(r'<a href="([^"]+)">(.*?)</a>',lambda m:f'[{re.sub("<[^>]+>","",m[2])}]({m[1]})',ref)
        ref=html.unescape(re.sub(r'<[^>]+>','',ref))
        emit(ref+'\n')
    emit('### Method and software source links\n')
    for name,url in [
        ('Arctic Shift API documentation','https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md'),
        ('NetworkX directed-to-undirected conversion','https://networkx.org/documentation/stable/reference/classes/generated/networkx.DiGraph.to_undirected.html'),
        ('NetworkX betweenness definition','https://networkx.org/documentation/networkx-3.3/reference/algorithms/generated/networkx.algorithms.centrality.betweenness_centrality.html'),
        ('NetworkX categorical assortativity','https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.assortativity.attribute_assortativity_coefficient.html'),
        ('SciPy bootstrap documentation','https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html'),
        ('Gephi documentation','https://docs.gephi.org/'),
        ('Cinelli et al., The echo chamber effect on social media','https://doi.org/10.1073/pnas.2023301118')]:
        emit(f'- [{name}]({url})')
    emit('\nThe current study implementation and saved data define the reported calculations. External documentation explains the methods; historical pilot artifacts are retained only for traceability.\n')
    DOC.write_text((source.split(MARKER)[0]+MARKER+'\n\n'+''.join(parts)).rstrip()+'\n',encoding='utf-8')
    print(f'Updated {DOC.name}: {len(DOC.read_text(encoding="utf-8").split()):,} whitespace-delimited words; {len(files)} aggregate CSVs inventoried; {len(refs)} report references.')


if __name__=='__main__':
    main()
