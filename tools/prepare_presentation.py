"""Prepare presentation content and editable evidence from study aggregates.

PowerPoint renders the native slide objects. This script does not draw images.
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/study'
DEST = ROOT / 'reports/presentation'
BLUE, ORANGE, GREEN, NAVY, GRAY = '2465A3', 'C46129', '258576', '173449', '586873'
slides = []


def read(relative):
    with (OUT / relative).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def slide(title, notes, source, section='main'):
    s = dict(title=title, notes=notes, source=source, section=section, elements=[])
    slides.append(s)
    return s


def text(s, value, x, y, w, h, size=21, color=NAVY, bold=False, align='left'):
    s['elements'].append(dict(type='text', text=value, x=x, y=y, w=w, h=h,
                              size=size, color=color, bold=bold, align=align))


def line(s, x, y, x2, y2, color='CBD4DA', arrow=False, width=1.3):
    s['elements'].append(dict(type='line', x=x, y=y, x2=x2, y2=y2, color=color, arrow=arrow, width=width))


def shape(s, x, y, w, h, color, kind='rect'):
    s['elements'].append(dict(type=kind, x=x, y=y, w=w, h=h, color=color))


def image(s, relative, x, y, w, h):
    assert (ROOT / relative).is_file(), relative
    s['elements'].append(dict(type='image', path=relative, x=x, y=y, w=w, h=h))


def takeaway(s, value):
    text(s, value, 48, 470, 864, 43, size=17, color=GRAY)


def points(s, items, x=48, y=137, w=850, step=80, size=23):
    for i, item in enumerate(items):
        text(s, item, x, y+i*step, w, step-12, size=size)


def table(s, headers, rows, widths, y=137, h=280, size=19):
    s['elements'].append(dict(type='table', headers=headers, rows=rows, widths=widths,
                              x=48, y=y, w=864, h=h, size=size))


def bars(s, categories, series, maximum, unit='', x=48, y=150, w=864, h=280,
         label_width=185, decimals=1, tick_values=None):
    """Editable bar-chart elements, with zero baseline and explicit values."""
    plot_x = x+label_width
    plot_w = w-label_width-70
    row_h = h/len(categories)
    ticks = tick_values or [0, maximum/2, maximum]
    for tick in ticks:
        tx = plot_x+plot_w*tick/maximum
        line(s, tx, y-5, tx, y+h-2, 'E3E8EB', width=.7)
        text(s, f'{tick:g}{unit}', tx-28, y+h+5, 62, 23, size=13, color=GRAY, align='center')
    for i, category in enumerate(categories):
        cy = y+i*row_h
        text(s, category, x, cy+1, label_width-12, row_h-2, size=17)
        bh = min(24, (row_h-9)/len(series))
        for k, ser in enumerate(series):
            value = float(ser['values'][i])
            by = cy+k*(bh+3)
            shape(s, plot_x, by, max(.5, plot_w*value/maximum), bh, ser['color'])
            label = f'{value:,.{decimals}f}{unit}'
            text(s, label, plot_x+plot_w*value/maximum+7, by-3, 72, bh+9, size=16, color=ser['color'], bold=True)
    if len(series)>1:
        legend_x = plot_x
        for ser in series:
            text(s, ser['name'], legend_x, y-40, 280, 28, size=17, color=ser['color'], bold=True)
            legend_x += 290
    s.setdefault('chart_data', []).append(dict(categories=categories, series=series, maximum=maximum, unit=unit))


def build():
    corpus = read('tables/superheroes_corpus.csv') + read('tables/consoles_corpus.csv')
    networks = read('tables/superheroes_networks.csv') + read('tables/consoles_networks.csv')
    names = {'marvelstudios':'Marvel', 'DC_Cinematic':'DC', 'PS5':'PS5', 'xbox':'Xbox'}
    by = {(r['subreddit'], r['window']):r for r in corpus}
    source_report = 'reports/course_report.html; MENTOR_STORY.md; research revision 61ae796'

    s = slide('Fandom Fault Lines',
        'Opening, about 40 seconds. We asked whether rival Reddit communities have separate audiences or overlapping ones. We studied content, reply networks and participation together. Our evidence shows measurable overlap, changing participation and network structure that depends on how replies are defined. We treat rivalry as a comparison setting rather than assuming hostility. Introduce Group 6 and all members. The main presentation ends at slide 27. Slides 28–35 support questions. Suggested main talk duration: 22–27 minutes.', source_report)
    s['cover'] = True
    text(s, 'Fandom\nFault Lines', 48, 72, 480, 145, size=50, bold=True)
    text(s, 'Rival Reddit communities,\nshared audiences and reply networks', 50, 235, 450, 85, size=25)
    text(s, 'Computational Social Media Analysis\nGroup 6', 50, 341, 440, 60, size=20, color=GRAY)
    text(s, 'Mayank Gupta  230553\nAnurag Kumar  230616\nJhalak Kapila  230576', 50, 419, 430, 81, size=17)
    image(s, 'outputs/study/figures/gephi_combined_superheroes_oct_all_replies.png', 515, 65, 410, 410)

    s = slide('The problem and our objective',
        'Separate subreddit names can suggest separate social worlds, but one account may participate in both. Conversely, the same audience overlap percentage can hide very different patterns over time. We wanted to describe where boundaries appear, how people interact and what they discuss. Participation, interaction and attitudes are different measurements. A reply can express agreement, criticism or a practical question. This is why a network picture alone cannot establish hostility or an echo chamber.', source_report)
    text(s, 'Do rival communities form distinct audiences,\nor do people and conversations connect them?', 48, 142, 864, 105, size=29, bold=True)
    points(s, ['Separate community names do not establish separate audiences.',
               'Shared participants may be occasional visitors or persistent participants.',
               'Our objective is to examine content, interaction and audience boundaries together.'], y=280, step=60, size=21)

    s = slide('Three research questions',
        'These are the three original dimensions, preserved in the expanded study. RQ1 concerns topics and sentiment about own and rival franchises. RQ2 concerns internal network organization and structural connectors. RQ3 concerns audience overlap and boundaries. The additional temporal, sampling and adjusted analyses strengthen these questions. They do not replace them. The original attitude question remains only partially answered because independent target-specific human annotation is unfinished.', 'MENTOR_STORY.md; study.json; reports/course_report.html')
    table(s, ['Question', 'What we examine', 'Evidence'], [
        ['RQ1  Content', 'Topics and sentiment concerning own and rival franchises', 'Mentions, VADER, shared NMF topics'],
        ['RQ2  Structure', 'Internal organisation and connector accounts', 'Reply graphs, centralities, communities'],
        ['RQ3  Boundaries', 'Audience overlap and cross-participation', 'Overlap, persistence, prior-group mixing']], [140,360,364], h=282)
    takeaway(s, 'Observed commenting defines participation. It does not establish personal fan allegiance.')

    s = slide('The research journey',
        'The project began with an approximately 19,000-comment Marvel/DC pilot. It established the workflow, but the collection scheme sampled the latest comments in slots and missed activity and reply relations. We audited the pipeline, found stale reporting and graph-construction issues, then expanded the observation design. We added a second rivalry and comparison audiences, tested sensitivity, and independently reconstructed the graphs. These extensions followed inspection of earlier findings, so the study is exploratory rather than preregistered.', 'PROJECT_STATUS.md; MENTOR_STORY.md; reports/course_report.html')
    table(s, ['Stage', 'What we did', 'Why it mattered'], [
        ['Pilot', 'Marvel/DC, approximately 19,000 comments', 'Established the initial workflow'],
        ['Audit', 'Checked collection, preprocessing and graph rules', 'Corrected measurement and reporting'],
        ['Expansion', 'Two rivalries, six audiences, 56 days', 'Broadened the comparison'],
        ['Sensitivity', 'Tested sampling, duration and activity', 'Qualified initial interpretations'],
        ['Verification', 'Rebuilt graphs and checked Gephi imports', 'Made results inspectable']], [120,420,324], h=290, size=18)
    takeaway(s, 'The journey improved the credibility of the conclusions, rather than targeting a larger effect.')

    s = slide('Methodology overview',
        'Read the method left to right. We first retrieve and validate records, then clean and organize them. EDA establishes coverage and the activity observed. The same prepared data supports the three analysis tracks. We compare results across graph definitions, sampling levels and activity-adjusted groups, then interpret them jointly. The analysis is iterative: robustness checks can revise our interpretation. Every displayed result is traceable to an aggregate table or verified graph.', 'tools/draw_methodology_flowchart.py; run_study.py; study.json')
    stages = [('Collect','Daily archive records'),('Prepare','Text and reply parents'),('Explore','Coverage and activity'),('Analyse','Three research questions'),('Verify','Sensitivity and audits')]
    for i,(head,detail) in enumerate(stages):
        x=48+i*176
        text(s,f'{i+1:02d}',x,140,150,45,32,BLUE,True)
        text(s,head,x,194,155,35,24,NAVY,True)
        text(s,detail,x,240,150,68,19)
        if i<4: line(s,x+136,211,x+166,211,BLUE,True,1.6)
    line(s,48,332,912,332)
    text(s,'Content analysis',48,365,275,35,23,BLUE,True)
    text(s,'Topics, mentions and sentiment',48,411,275,58,20)
    text(s,'Network analysis',349,365,275,35,23,BLUE,True)
    text(s,'Directed replies, structure and Gephi',349,411,275,58,20)
    text(s,'Audience analysis',650,365,262,35,23,BLUE,True)
    text(s,'Overlap, persistence and mixing',650,411,262,58,20)

    s = slide('Study design and observation windows',
        'The first UTC window is 3 September to 1 October 2026, end exclusive. The second is 1 October to 29 October, end exclusive. Each lasts 28 days, making a pooled 56-day period. Four rivalry communities have detailed text and reply records. StarWars and lotr supply lighter author-time records for overlap comparisons. The design gives 6 times 56 equals 336 expected daily files. Adjacent windows are not independent replications because accounts can recur.', 'study.json; outputs/study/collection_inventory.csv')
    table(s,['Role','Communities','Analysis scope'],[
        ['Superhero rivalry','r/marvelstudios, r/DC_Cinematic','Content, networks and participation'],
        ['Console rivalry','r/PS5, r/xbox','Content, networks and participation'],
        ['Comparison audiences','r/StarWars, r/lotr','Audience overlap']], [190,355,319], h=215,size=18)
    text(s,'First window\n3–30 September 2026',48,390,400,65,23,BLUE,True)
    text(s,'Second window\n1–28 October 2026',510,390,400,65,23,ORANGE,True)
    takeaway(s,'All dates use UTC. Two equal 28-day windows provide 56 observed days.')

    s = slide('Data collection and provenance',
        'The Arctic Shift archive API provides the comment records. Collection paginates backwards in batches of up to 100 and keeps records within each declared UTC day. We retry temporary failures with backoff. Timestamp ambiguities and safety-cap exhaustion fail explicitly. Files are installed only after ID, schema and time-range checks. New downloads record retrieval metadata and SHA-256 checksums. Some inherited caches do not have historical request manifests. Complete expected files do not prove complete coverage of all Reddit activity.', 'src/study_data.py; outputs/study/collection_inventory.csv; https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md')
    points(s,['Arctic Shift archive API, collected in daily UTC batches',
              'Backward pagination, duplicate-ID checks and retry handling',
              'Validate timestamps and schema before accepting each daily file',
              '336 expected daily files pass coverage checks'],step=72)
    takeaway(s,'Coverage describes the retrieved archive. New-download checksums support provenance.')

    s = slide('Preprocessing preserves different denominators',
        'Participation retains identifiable accounts after missing or deleted author and documented bot-list exclusions, even if their text is unusable. Content analysis additionally removes missing or removed bodies, duplicate IDs, URL clutter, very short text and text without Latin letters. This is not a comprehensive language classifier or bot detector. Parent authors are resolved from local comments and, when necessary, comment or submission ID lookups, including parents outside the study window. Pseudonyms remain consistent across communities. Raw text and account-level derivatives stay local.', 'src/study_data.py; src/study_analysis.py; src/study_network.py; outputs/study/tables/*_corpus.csv')
    text(s,'Participation dataset',48,140,405,40,25,BLUE,True)
    points(s,['Identifiable accounts after documented exclusions','Includes comments with unusable text','Supports overlap and activity comparisons'],x=48,y=205,w=400,step=70,size=21)
    text(s,'Content dataset',510,140,402,40,25,ORANGE,True)
    points(s,['Cleaned comment text','852,512 usable comments from the four rivalry communities','Supports mentions, sentiment and topics'],x=510,y=205,w=400,step=70,size=21)
    takeaway(s,'Reply-parent resolution is a separate relational step. Consistent pseudonyms support account matching.')

    inventory=read('collection_inventory.csv')
    totals={}
    for r in inventory: totals[r['subreddit']]=totals.get(r['subreddit'],0)+int(r['rows'])
    assert sum(totals.values())==1168638
    s = slide('EDA establishes an uneven observed corpus',
        'Across six audiences we observe 1,168,638 archive records. The four rivalry communities account for 888,719 raw records, and 852,512 pass content filters. The chart uses raw archive counts, which differ from participation or content counts. Marvel is the largest collected community and lotr the smallest. Unequal activity means we must compare rates and define denominators rather than interpret raw totals as attitudes or popularity. We also check active accounts, weekly activity and missing parents.', 'outputs/study/collection_inventory.csv; outputs/study/tables/*_corpus.csv')
    cats=['marvelstudios','DC_Cinematic','PS5','xbox','StarWars','lotr']
    bars(s,[names.get(c,c) for c in cats],[dict(name='Archive records',color=BLUE,values=[totals[c] for c in cats])],350000,h=280,decimals=0,tick_values=[0,100000,200000,300000])
    takeaway(s,'1,168,638 raw archive records across all six communities. Detailed content analysis uses four communities.')

    s = slide('Sampling changes the apparent audience boundary',
        'We reran overlap calculations after random comment subsampling and with nested observation durations. For Marvel/DC in the first window, the mean Jaccard overlap with 10 percent of comments is 3.15 percent, compared with 6.78 percent for the full collected window. A shared account can look exclusive if one side of its activity is missed. These seeded experiments show observation sensitivity. They do not exactly reproduce the original pilot sampling design, and the replicate range is not an inferential confidence interval.', 'outputs/study/tables/superheroes_sampling.csv; outputs/study/tables/superheroes_overlap.csv; outputs/study/tables/*_duration.csv')
    sampling=read('tables/superheroes_sampling.csv')
    vals=[]
    for frac in [.1,.25,.5]:
        v=[float(r['jaccard_pct']) for r in sampling if r['window']=='sep' and float(r['fraction'])==frac and r['min_comments']=='1']
        vals.append(sum(v)/len(v))
    overlap=read('tables/superheroes_overlap.csv')
    vals.append(float(next(r for r in overlap if r['window']=='sep' and r['min_comments']=='1')['jaccard_pct']))
    bars(s,['10% retained','25% retained','50% retained','Full window'],[dict(name='Jaccard overlap',color=BLUE,values=vals)],8,unit='%',h=240,decimals=2)
    takeaway(s,'Marvel/DC, first window. Sampling means use five seeded draws below 100% of comments.')

    s = slide('How we build a reply network',
        'Use this toy example slowly. A replies to B twice, so A to B has weight two. B replies to A once, so B to A has weight one. These are two directed edges representing three reply events. For the undirected Louvain projection, reciprocal weights sum to three. A node is an account. A directed edge links the replier to the parent author. Same-thread presence or shared community participation does not create an edge. Self-replies are excluded and counted. Observed commenters remain nodes even when isolated. Parent-only accounts have an explicit marker.', 'src/study_network.py; src/study_network_review.py; MENTOR_STORY.md')
    for label,x in [('A',190),('B',600)]:
        shape(s,x,155,100,100,BLUE,'ellipse'); text(s,label,x,173,100,65,40,'FFFFFF',True,'center')
    line(s,300,180,590,180,BLUE,True,3)
    text(s,'2 replies',385,140,150,35,22,BLUE,True,'center')
    line(s,590,235,300,235,ORANGE,True,3)
    text(s,'1 reply',385,257,150,35,22,ORANGE,True,'center')
    table(s,['Element','Operational definition'],[['Node','An account'],['Directed edge','Replier to parent author'],['Weight','Number of observed replies in that direction']], [210,654],y=325,h=115,size=18)
    takeaway(s,'Toy example: 2 directed edges, 3 reply events. The undirected projection has weight 3.')

    s = slide('Graph definitions and network measures',
        'We construct sixteen original networks: four rivalry communities, two windows and two edge definitions. All-reply graphs include replies to original submissions and replies to comments. Comment-only graphs exclude replies to submissions. Degree measures distinct neighbors, strength counts reply events, and weighted PageRank describes incoming prominence. Directed betweenness uses unweighted paths and up to 128 sampled sources. Louvain uses the undirected reciprocal-sum graph. Reciprocity, components and k-core provide additional structure. Reply frequency is not interpreted as a distance.', 'src/study_network.py; outputs/study/tables/*_networks.csv')
    text(s,'16 networks = 4 communities × 2 windows × 2 definitions',48,130,864,55,26,BLUE,True)
    table(s,['Measure','What it describes'],[['Degree and strength','Distinct reply partners and total reply events'],['Weighted PageRank','Prominence through incoming reply links'],['Betweenness','Potential connectors along directed shortest paths'],['Louvain modularity','Organization in the undirected weighted projection'],['Components and reciprocity','Connectivity and mutual reply relationships']], [270,594],y=205,h=240,size=18)
    takeaway(s,'All replies and comment-only replies test how thread starters affect apparent connectivity.')

    s = slide('Gephi analysis and verification',
        'Gephi serves two purposes: inspecting exported graphs and visualizing their structure. The official Gephi Toolkit imports the graph, verifies counts and degrees, recomputes weighted PageRank, and saves and reopens native projects. We have eight individual-community projects and four combined second-window projects. The FULL workspace retains the original graph. The FOCUS workspace applies a display filter and ForceAtlas2. Numerical study measures come from full graphs. A separate algorithm reconstructs all sixteen original graphs from raw parent-author joins and confirms exact edges and weights.', 'tools/GephiStudy.java; tools/build_gephi.py; tools/build_combined_gephi.py; outputs/study/network_review/edge_audit.csv; outputs/study/gephi_validation.csv; GEPHI_GUIDE.md')
    table(s,['Purpose','What we do'],[['Verify the export','Check node, edge and degree counts after import'],['Inspect full structure','Retain a FULL workspace with original attributes'],['Create readable views','Use a separate FOCUS workspace and ForceAtlas2'],['Preserve the analysis','Save and reopen native .gephi projects']], [250,614],h=260,size=21)
    takeaway(s,'12 native Gephi projects are available. Independent raw-record reconstruction verifies all 16 original graphs.')

    for pair,title,n,e,dn,de,labels in [
        ('superheroes','Gephi view of Marvel and DC',61356,138992,782,2801,('Marvel-only','DC-only')),
        ('consoles','Gephi view of PS5 and Xbox',50692,85515,577,1058,('PS5-only','Xbox-only'))]:
        s=slide(title,
            f'This is the combined second-window comment-reply network for {pair}. The full graph has {n:,} nodes and {e:,} directed edges. The display has {dn:,} nodes and {de:,} edges. Blue and orange describe first-window participation in only one side, green describes participation in both, and gray indicates no observed first-window participation. These are prior participation categories, not Louvain classes or fan allegiance. Node size uses log-scaled full incoming strength. The display selects prominent accounts and repeated interactions. Visually concentrated colors coexist with connections, but layout distances and the display composition cannot establish population segregation or exceptional brokerage. Numerical mixing follows later.',
            f'outputs/study/figures/gephi_combined_{pair}_oct_comment_replies.png; outputs/study/network_review/combined_exports.csv; tools/GephiStudy.java')
        image(s,f'outputs/study/figures/gephi_combined_{pair}_oct_comment_replies.png',48,113,540,345)
        text(s,'Prior participation',623,130,290,35,24,NAVY,True)
        for i,(label,color) in enumerate([(labels[0],BLUE),(labels[1],ORANGE),('Both',GREEN),('Unobserved','999999')]):
            text(s,label,623,185+i*43,285,35,22,color,True)
        text(s,f'Displayed\n{dn:,} nodes   {de:,} edges',623,376,285,70,21)
        takeaway(s,f'October comment replies. Full graph: {n:,} nodes and {e:,} directed edges. Display selection limits interpretation.')

    s = slide('Thread starters explain much of the connectivity',
        'This chart compares the percentage of nodes in the largest weak component under the two graph definitions. A weak component ignores direction when assessing connectivity. The denominator retains all observed commenters, including isolates. In September Xbox the component falls from 98.61 percent in the all-reply graph to 53.33 percent after removing replies to original posts. Across communities, all-reply coverage is approximately 96–99 percent, versus 53–72 percent for comment-only graphs. This identifies thread architecture as an important explanation for apparent cohesion.', 'outputs/study/tables/superheroes_networks.csv; outputs/study/tables/consoles_networks.csv')
    keys=[(a,b) for a in names for b in ['sep','oct']]
    ns={(r['subreddit'],r['window'],r['variant']):r for r in networks}
    bars(s,[f'{names[a]} {b.title()}' for a,b in keys],[dict(name='All replies',color=BLUE,values=[float(ns[a,b,'all_replies']['largest_component_pct']) for a,b in keys]),dict(name='Comment replies only',color=ORANGE,values=[float(ns[a,b,'comment_replies']['largest_component_pct']) for a,b in keys])],100,unit='%',y=150,h=288,label_width=150)
    takeaway(s,'Largest weak component as a percentage of nodes. Removing replies to posts changes the network substantially.')

    s = slide('Matched comparisons qualify the connector claim',
        'Some unadjusted top-betweenness selections contain more shared accounts than their community baseline. The question is whether this remains surprising among accounts with similar activity and degree. We compare top-20 positive-betweenness selections, including ties, to random selections preserving matching strata. Across 32 matching, graph and period comparisons, none passes the Holm-adjusted 0.05 enrichment threshold. This does not establish equivalence or no connector role. Approximate betweenness, coarse matching and small selected sets limit power. The displayed chart shows all-reply networks with activity-and-degree matching.', 'outputs/study/advanced/matched_connectors.csv; src/study_advanced.py')
    matched=read('advanced/matched_connectors.csv')
    lookup={(r['subreddit'],r['window']):r for r in matched if r['variant']=='all_replies' and r['matching']=='activity_and_degree'}
    bars(s,[f'{names[a]} {b.title()}' for a,b in keys],[dict(name='Observed among connectors',color=BLUE,values=[float(lookup[a,b]['observed_shared_pct']) for a,b in keys]),dict(name='Matched expectation',color=ORANGE,values=[float(lookup[a,b]['matched_expected_shared_pct']) for a,b in keys])],100,unit='%',y=150,h=288,label_width=150)
    takeaway(s,'No enrichment comparison survives Holm adjustment across 32 tests. This is not an equivalence result.')

    s = slide('Rival audiences have measurable overlap',
        'The pooled 56-day calculation deduplicates accounts across both windows. Marvel/DC shares 8,807 commenters. That is 12.84 percent of Marvel commenters and 22.07 percent of DC commenters. The asymmetry matters because the audience sizes differ. PS5/Xbox shares 4,978 accounts, representing 10.70 and 11.23 percent. Jaccard divides shared accounts by the union. Marvel/DC has the largest Jaccard overlap among the fifteen selected community pairs in each window. This is conditional on our six-community comparison set, not a Reddit-wide ranking.', 'outputs/study/tables/superheroes_overlap.csv; outputs/study/tables/consoles_overlap.csv; outputs/study/tables/all_pair_overlap.csv')
    table(s,['56-day pair','Shared accounts','Shared / A','Shared / B','Jaccard'],[
        ['Marvel / DC','8,807','12.84%','22.07%','8.83%'],
        ['PS5 / Xbox','4,978','10.70%','11.23%','5.80%']], [230,180,150,150,154],h=177,size=21)
    text(s,'Directional overlap reveals asymmetry',48,355,864,40,25,BLUE,True)
    text(s,'A larger fraction of DC commenters also appears in Marvel than the reverse.',48,408,864,60,24)
    takeaway(s,'Threshold: at least one comment in each community. A and B follow the pair order shown.')

    s = slide('Pooled sharing rarely means persistent sharing',
        'Persistent sharing means commenting in both communities in each of the two windows. Among all pooled shared accounts, only 1,577 of 8,807 superhero accounts, or 17.9 percent, meet this definition. For consoles it is 945 of 4,978, or 19.0 percent. Most pooled shared accounts qualify in only one window or participate sequentially across the windows without sharing in either individual window. About 36 percent of the first-window shared cohort is shared again in the second, but that uses a different denominator. Do not substitute these percentages for one another.', 'outputs/study/advanced/persistence.csv; outputs/study/advanced/transitions.csv')
    persistence=read('advanced/persistence.csv')
    pr=[next(r for r in persistence if r['pair']==p and r['min_comments']=='1' and r['pattern']=='both_in_each_window') for p in ['superheroes','consoles']]
    bars(s,['Marvel / DC','PS5 / Xbox'],[dict(name='Persistent among pooled shared accounts',color=GREEN,values=[float(r['pct_pooled_shared']) for r in pr])],100,unit='%',y=160,h=130,label_width=190)
    text(s,'1,577 of 8,807\nMarvel/DC shared accounts',48,365,400,75,25,BLUE,True)
    text(s,'945 of 4,978\nPS5/Xbox shared accounts',510,365,400,75,25,ORANGE,True)
    takeaway(s,'Persistent means both communities in both windows. All percentages here use pooled shared accounts as the denominator.')

    s = slide('Prior-participation assortativity rises in the union',
        'We measure reply-event-weighted categorical assortativity using known first-window participation labels. For October comment replies, Marvel and DC separately have coefficients 0.013 and 0.003, while the union reaches 0.347. PS5 and Xbox separately are 0.013 and 0.032, while their union reaches 0.387. Different groups prefer different discussion spaces, which changes the combined structure. This is an aggregation effect, not a causal test of avoidance or an ideology measure. Only 52.50 percent and 50.09 percent of reply events have both endpoints observed in the first window. Opposite prior-exclusive groups still exchange 4,908 superhero and 2,240 console reply events.', 'outputs/study/network_review/mixing_summary.csv; src/study_network_review.py')
    table(s,['Comment-reply graph','A layer','B layer','Combined','Known-event coverage'],[
        ['Marvel / DC','0.013','0.003','0.347','52.50%'],
        ['PS5 / Xbox','0.013','0.032','0.387','50.09%']], [260,120,120,140,224],h=170,size=19)
    text(s,'Combined coefficients greatly exceed the within-subreddit coefficients.',48,351,864,66,27,BLUE,True)
    takeaway(s,'Coefficients condition on known prior labels. The combined picture does not isolate selective avoidance within discussions.')

    s = slide('Rival attention is asymmetric',
        'Our dictionaries identify explicit franchise references. DC commenters mention Marvel more often than Marvel commenters mention DC. Xbox commenters mention PlayStation more often than PS5 commenters mention Xbox. These percentages divide comments with rival mentions, including both-franchise mentions, by usable content comments. They depend on dictionary coverage and alias ambiguity. A mention indicates attention, and the following slide examines tone. It does not by itself indicate hostility.', 'outputs/study/tables/*_corpus.csv; study.json')
    subs=list(names)
    bars(s,['Marvel mentions DC','DC mentions Marvel','PS5 mentions Xbox','Xbox mentions PS'],[
        dict(name='First window',color=BLUE,values=[float(by[a,'sep']['rival_mention_pct']) for a in subs]),
        dict(name='Second window',color=ORANGE,values=[float(by[a,'oct']['rival_mention_pct']) for a in subs])],8,unit='%',y=155,h=260,label_width=235,decimals=2)
    takeaway(s,'Explicit rival mentions as a percentage of usable content comments, under the specified dictionaries.')

    s = slide('Automated sentiment gives a mixed account of rivalry',
        'The main tests compare own-only comments to rival-mentioning comments with original and adapted VADER. Three of eight main adapted-VADER any-rival comparisons survive Holm adjustment under both author and thread clustering sensitivities: DC in both windows and Marvel in October. All have negative own-minus-rival differences, meaning rival-mentioning comments score more positively on average. The displayed paired-author figure is a separate sensitivity that gives each eligible author equal weight. Its descriptive bootstrap intervals are unadjusted. Negative overall text sentiment is not equivalent to target-directed opposition, so independent human validation remains necessary.', 'outputs/study/figures/within_author_sentiment.png; outputs/study/advanced/paired_sentiment.csv; outputs/study/tables/*_tests.csv; https://doi.org/10.1017/psrm.2024.35')
    image(s,'outputs/study/figures/within_author_sentiment.png',48,118,585,326)
    text(s,'Whole-comment tone',665,145,245,40,24,BLUE,True)
    text(s,'No consistent evidence that rival mentions are more negative.',665,205,245,110,23)
    text(s,'Target-specific human validation remains unfinished.',665,340,245,100,22,ORANGE,True)
    takeaway(s,'Figure: paired authors, own-only minus rival-mentioning sentiment. Intervals are descriptive and unadjusted.')

    s = slide('Topic models describe recurring discussion themes',
        'We fit one pooled TF-IDF and NMF model per rivalry across both periods, using balanced sampling. Candidate topic counts are six, eight, ten and twelve, compared with in-sample coherence. The selected models have six superhero and ten console factors. Keywords suggest character/franchise discussions, Green Lantern, Game Pass, physical versus digital purchases and hardware. Some factors capture generic conversation or moderation. Between 31.7 and 37.4 percent of content comments lack sufficient topical vocabulary and remain unassigned. These are exploratory model factors rather than validated semantic classes.', 'outputs/study/tables/superheroes_topics.csv; outputs/study/tables/consoles_topics.csv; src/study_analysis.py')
    table(s,['Model','Illustrative keywords','Interpretation'],[
        ['Superheroes, 6 factors','batman, superman, dcu, gunn','Franchise and character discussion'],
        ['Superheroes','green, lantern, lanterns, ring','Green Lantern discussion'],
        ['Consoles, 10 factors','game, pass, game pass','Game Pass and games'],
        ['Consoles','disc, digital, physical, drive','Ownership and purchase format']], [235,330,299],h=255,size=19)
    takeaway(s,'31.7–37.4% of content comments remain unassigned. Generic factors limit substantive topic labels.')

    s = slide('Shared participants return more often',
        'Return means at least one observed comment in either community of the pair during the next window. We compare initially shared and exclusive participants after standardizing first-window activity within common-support bins. The adjusted differences remain 13.08 percentage points relative to Marvel-only, 7.23 relative to DC-only, 15.28 relative to PS5-only and 10.95 relative to Xbox-only. One-comment exclusive accounts lack a comparable shared group and are excluded from the adjusted population. The intervals use 5,000 bootstrap draws with fixed stratum weights and are descriptive, without multiplicity adjustment. This supports an association with later engagement, not a causal effect of cross-participation.', 'outputs/study/advanced/retention.csv; src/study_advanced.py')
    ret=[r for r in read('advanced/retention.csv') if r['outcome']=='observed_in_pair']
    labels={('superheroes','a_only'):'Marvel-only',('superheroes','b_only'):'DC-only',('consoles','a_only'):'PS5-only',('consoles','b_only'):'Xbox-only'}
    rows=[[labels[r['pair'],r['reference']],f"+{float(r['adjusted_difference_pp']):.2f} pp",f"{float(r['ci_low_pp']):.2f} to {float(r['ci_high_pp']):.2f} pp"] for r in ret]
    table(s,['Shared compared with','Adjusted difference','Descriptive 95% interval'],rows,[310,240,314],h=235,size=22)
    text(s,'The association remains after observed activity adjustment.',48,399,864,60,25,BLUE,True)
    takeaway(s,'Return = observed again anywhere in the pair. Common-support restriction changes the target population.')

    s = slide('Answers to our research questions',
        'Return explicitly to the original questions. For content we identify asymmetric attention and exploratory themes, but target-directed attitudes remain only partially addressed. For structure we find organized reply networks whose connectivity is sensitive to thread starters. Shared-account connector enrichment is not supported after the specified activity and degree matching. For boundaries we find measurable but often temporary overlap, along with direct replies between prior participation groups. These are bounded claims about observed commenting in the selected windows.', source_report)
    table(s,['Question','What the evidence supports','Boundary of the claim'],[
        ['RQ1  Content','Asymmetric rival attention and exploratory themes','Rival-directed hostility still needs validation'],
        ['RQ2  Structure','Thread-sensitive connectivity and measurable organization','Centrality does not establish causal influence'],
        ['RQ3  Boundaries','Measurable overlap, limited persistence and group interaction','Commenting is distinct from allegiance or readership']], [140,385,339],h=285,size=20)

    s = slide('Limitations and the next useful evidence',
        'Two purposively chosen rivalries and adjacent windows cannot establish seasonal stability or generality across all fandoms. Archive completeness, alias coverage and undocumented bots remain uncertain. The null ensemble is small, betweenness is approximate and matching is coarse. We should prioritize independent human annotation of overall tone and target-specific stance. The prepared blinded sheets are not labelled yet. If those labels inform tuning, evaluation requires a separate untouched sample. Broader temporal claims would need separated or event-aligned windows chosen before collection. Another rivalry should answer a substantive comparison question, not be selected to obtain a stronger effect.', 'PROJECT_STATUS.md; ANNOTATION_GUIDE.md; ADVANCED_METHODS.md')
    text(s,'Current limits',48,140,400,40,25,ORANGE,True)
    points(s,['Two rivalries and 56 adjacent days','Archive and dictionary coverage','Approximate centrality and coarse matching','Unfinished human stance validation'],x=48,y=202,w=400,step=58,size=21)
    text(s,'Next evidence',510,140,400,40,25,BLUE,True)
    points(s,['Independent blinded annotation','Untouched evaluation sample','Separated or event-aligned windows','A justified additional comparison'],x=510,y=202,w=400,step=58,size=21)
    takeaway(s,'More comments alone cannot resolve a mismatch between whole-comment sentiment and target-directed attitudes.')

    s = slide('What we finally learned',
        'Closing, about 45 seconds. The project moved beyond a small pilot and an expected rivalry narrative. Rival audiences are distinct but overlapping. Most pooled shared participation is not persistent in both windows. Reply connectivity depends on the role of thread starters, and the combined graph requires comparison with its individual layers. The strongest contribution is an auditable joint analysis that distinguishes audiences, interactions and attitudes. Invite questions. If time permits, demonstrate the FULL and FOCUS workspaces in Gephi using the backup checklist on slide 30.', source_report)
    text(s,'Rival audiences overlap,\nbut the overlap changes over time.',48,140,864,110,34,BLUE,True)
    points(s,['Reply structure depends strongly on thread mechanics.',
              'Gephi makes the graph inspectable when its construction and filters are explicit.',
              'Our contribution is a reproducible, bounded account of these relationships.'],y=295,step=62,size=23)

    s = slide('Backup  Full network statistics',
        'All values describe full all-reply graphs. Nodes may include parent-only accounts, so their count can exceed the number of observed commenters. Edges count distinct ordered account pairs. Modularity is weighted Louvain on the reciprocal-sum undirected projection. Modularity from an unweighted null comparison must not be compared directly to this weighted statistic. Reciprocity concerns directed edge pairs. Source CSVs include density, components, isolates and clustering if mentors ask.', 'outputs/study/tables/*_networks.csv','backup')
    rows=[]
    for a,b in keys:
        r=ns[a,b,'all_replies']; rows.append([f'{names[a]} {b.title()}',f"{int(r['nodes']):,}",f"{int(r['edges']):,}",f"{float(r['reciprocity']):.3f}",f"{float(r['modularity_weighted']):.3f}"])
    table(s,['Graph','Nodes','Edges','Reciprocity','Weighted Q'],rows,[230,165,165,155,149],h=310,size=18)

    s = slide('Backup  The Gephi display is a selected subset',
        'The combined display first selects the top 1,000 accounts by full-graph PageRank, keeps the largest weak component of that cap, retains repeated edges with weight at least two, and removes resulting isolates. For the superhero comment-reply display, 30.1 percent of shown accounts have prior both participation compared with 5.4 percent of the full graph. Unobserved prior accounts decline from 58.1 percent to 13.9 percent. This large shift demonstrates why a visualization cannot estimate the prevalence of shared participation. Metrics and mixing use full graphs.', 'reports/course_report.html, Table 5; tools/GephiStudy.java; outputs/study/networks/combined_superheroes_oct_comment_replies_full.gexf','backup')
    table(s,['Prior participation','Full graph','Display'],[['Marvel-only','14,917 (24.3%)','225 (28.8%)'],['DC-only','7,481 (12.2%)','213 (27.2%)'],['Both','3,322 (5.4%)','235 (30.1%)'],['Unobserved','35,636 (58.1%)','109 (13.9%)']], [330,267,267],h=235,size=20)
    takeaway(s,'Top 1,000 by PageRank, largest weak component, edge weight ≥ 2, then remove resulting isolates.')

    s = slide('Backup  Gephi demonstration sequence',
        'Prepare the local files before presenting. Open combined_superheroes_oct_comment_replies_native.gephi, then show the FULL workspace counts and the directed graph type. Use Data Laboratory to explain prior_group, current_group, weight_a, weight_b and total weight. Switch to FOCUS and state the filter before discussing the layout. Explain the color legend and log-scaled full incoming-strength size. Open the console counterpart for comparison. Keep the all-reply variants available to explain graph-definition sensitivity. The saved native workspaces already contain their layouts. Do not rerun a layout merely to change the expected appearance.', 'GEPHI_GUIDE.md; outputs/study/networks/combined_superheroes_oct_comment_replies_native.gephi; outputs/study/networks/combined_consoles_oct_comment_replies_native.gephi','backup')
    table(s,['Step','What to show'],[['1','FULL workspace: directed graph, node and edge counts'],['2','Data Laboratory: prior_group, weight_a, weight_b and weight'],['3','FOCUS workspace: explain the display selection'],['4','Preview: colours, node size and ForceAtlas2 layout'],['5','Console counterpart and all-reply sensitivity']], [110,754],h=280,size=21)
    takeaway(s,'Numerical checks belong to the full graph. Layout distance is illustrative.')

    s = slide('Backup  Statistical choices and validation',
        'The main content tests use rank-biserial effects and separate author and thread cluster bootstrap sensitivities with 1,000 draws. Holm adjustment spans scorer, mention definition and community contrasts within each pair-period. These are not simultaneous two-way cluster estimates. Advanced paired-author and return analyses use 5,000 draws and descriptive unadjusted intervals. The matched connector family applies Holm across 32 comparisons. Network nulls use ten requested degree-preserving rewires on an unweighted projection and are descriptive. The offline test record is 64 passing and one optional pretrained-model skip. Blinded human labels remain blank.', 'ADVANCED_METHODS.md; src/study_analysis.py; src/study_advanced.py; PROJECT_STATUS.md','backup')
    table(s,['Analysis','Choice','Interpretation'],[['Content comparisons','Author and thread cluster sensitivities, Holm adjustment','Whole-comment sentiment only'],['Matched connectors','Activity / degree strata, 32-test Holm family','No corrected enrichment'],['Return and paired authors','5,000 bootstrap draws','Descriptive unadjusted intervals'],['Network null','10 degree-preserving rewires','Descriptive topology comparison'],['Verification','64 tests pass, 1 optional skip','Implementation checks']], [230,390,244],h=285,size=18)

    s = slide('Backup  Code and evidence map',
        'The canonical study runner is run_study.py with study.json. The legacy pilot runner remains for provenance. Collection and validation live in study_data.py. Study analysis produces corpus summaries, overlap, content tests and topics. Network construction and connector measures live in their respective modules. Advanced analysis computes temporal and adjusted comparisons. Network review independently reconstructs edges and measures prior participation mixing. Java Gephi helpers create native projects. Published outputs are aggregates and unlabelled figures, while raw text and detailed account networks remain local.', 'README.md; run_study.py; src/; tools/','backup')
    table(s,['Stage','Implementation','Evidence'],[['Collection','src/study_data.py','collection_inventory.csv'],['Content and overlap','src/study_analysis.py','tables/*_corpus, overlap, tests, topics.csv'],['Reply networks','src/study_network.py','tables/*_networks.csv'],['Temporal and adjusted','src/study_advanced.py','advanced/*.csv'],['Independent audit','src/study_network_review.py','network_review/edge_audit.csv'],['Gephi','tools/GephiStudy.java','Native projects and validation tables']], [210,330,324],h=295,size=17)

    s = slide('Backup  Research that informed the design',
        'The report reviews twelve recent papers from 2024–2026. These first six motivate separating participation, interaction and community structure. Cirulli and colleagues use validated Reddit communities and content to examine polarization. Goglia and Vega model evolving Reddit threads. Blondel and colleagues discuss Louvain after fifteen years. Yuan and colleagues examine behavioral homophily. Xia and colleagues study cross-party interactions and subsequent participation. Russo and colleagues use matched comparisons to study fringe recruitment. Their contexts do not determine expected effects for entertainment fandoms.', 'https://doi.org/10.1140/epjds/s13688-026-00707-5\nhttps://doi.org/10.1007/s41109-024-00654-y\nhttps://doi.org/10.1088/1742-5468/ad6139\nhttps://doi.org/10.1145/3696410.3714618\nhttps://doi.org/10.1609/icwsm.v19i1.35918\nhttps://doi.org/10.1609/icwsm.v18i1.31393','backup')
    table(s,['Study','Design implication'],[['Cirulli et al., 2026, EPJ Data Science (in press)','Separate participation and interaction boundaries'],['Goglia & Vega, 2024, Applied Network Science','Model reply threads explicitly'],['Blondel et al., 2024, JSTAT','Interpret Louvain as structural optimization'],['Yuan et al., 2025, The Web Conference','Distinguish behavior from topical similarity'],['Xia et al., 2025, ICWSM','Order participation observations over time'],['Russo et al., 2024, ICWSM','Use suitable comparison groups']], [490,374],h=300,size=18)

    s = slide('Backup  Participation and attitude measurement',
        'Machado and colleagues provide a 2025 preprint on contribution concentration, and Oswald and colleagues experimentally study participation in online political discussion. Burnham distinguishes sentiment and stance and discusses practical validation. Jamadi Khiabani and Zubiaga survey cross-target stance detection. Nguyen and Kim show that external information can degrade language-model stance performance. Gera and Neal study linguistic complexity and stance errors. These studies support measurement caution, not a claim that language models cannot work. Foundational method references are Hutto and Gilbert 2014 for VADER and Jacomy and colleagues 2014 for ForceAtlas2. Full citations and DOI links appear in the report.', 'https://doi.org/10.48550/arXiv.2503.02661\nhttps://doi.org/10.1126/sciadv.ady8022\nhttps://doi.org/10.1017/psrm.2024.35\nhttps://doi.org/10.1016/j.eswa.2025.127790\nhttps://doi.org/10.18653/v1/2025.findings-acl.764\nhttps://doi.org/10.18653/v1/2026.starsem-conference.20\nhttps://doi.org/10.1609/icwsm.v8i1.14550\nhttps://doi.org/10.1371/journal.pone.0098679','backup')
    table(s,['Study','Design implication'],[['Machado et al., 2025, arXiv preprint','Account for concentrated activity'],['Oswald et al., 2025, Science Advances','Visible participants differ from silent readers'],['Burnham, 2025, PSRM','Validate target-directed attitude measures'],['Jamadi Khiabani & Zubiaga, 2025, ESWA','Check target transfer and evaluation'],['Nguyen & Kim, 2025, Findings of ACL','Avoid assuming LLM labels are ground truth'],['Gera & Neal, 2026, *SEM','Inspect linguistic sources of stance errors']], [490,374],h=300,size=18)
    takeaway(s,'Foundational methods: Hutto & Gilbert (2014), VADER. Jacomy et al. (2014), ForceAtlas2. Full citations are in the report.')

    s = slide('Backup  Questions we can answer precisely',
        'Use these as short answers, then point to the relevant evidence. We do not claim the source archive is complete. Sixteen exact graph reconstructions validate our implementation. We do not call the detected communities ideological factions. The all-reply versus comment-only comparison measures sensitivity to thread starters. Stronger target-specific attitude claims need independent annotation. We would justify new periods or communities through a research design rather than searching for significant results. If asked about individual contributions, use the report allocation only after all members confirm it against their actual work.', 'MENTOR_STORY.md; PROJECT_STATUS.md; GEPHI_GUIDE.md','backup')
    table(s,['Likely question','Short answer'],[['Is the graph correct?','Exact reconstruction checks nodes, directed edges and weights.'],['Does a Gephi cluster prove an echo chamber?','The layout and prior participation labels do not establish ideology.'],['Are shared users exceptional connectors?','The specified matched tests do not support corrected enrichment.'],['Have we proved hostility?','No. Independent target-specific human validation is unfinished.'],['Would longer periods help?','They could address temporal generality with a specified design.']], [340,524],h=290,size=19)

    assert len(slides)==35, len(slides)
    assert all(s['notes'] and s['source'] for s in slides)
    sources=sorted({str(p.relative_to(ROOT)) for p in OUT.rglob('*.csv') if p.parent in [OUT,OUT/'tables',OUT/'advanced',OUT/'network_review']})
    payload=dict(title='Fandom Fault Lines', authors=['Mayank Gupta','Anurag Kumar','Jhalak Kapila'],
                 group='Group 6', main_slides=27, slide_count=len(slides), size=[960,540], font='Calibri',
                 slides=slides, evidence_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources})
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'presentation_content.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'Prepared {len(slides)} slides: 27 main slides and 8 backup slides, with speaker notes and sources.')


if __name__=='__main__':
    build()
