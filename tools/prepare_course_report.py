"""Prepare report-only figures and evidence checks without rerunning research."""
import ast
import hashlib
import json
import re
from html import unescape
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/study'
REPORT = ROOT / 'reports'


def plain(text):
    return unescape(re.sub('<[^>]+>', ' ', text))


def main():
    assets = REPORT / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    frames = [pd.read_csv(OUT / f'tables/{p}_networks.csv') for p in ['superheroes', 'consoles']]
    networks = pd.concat(frames, ignore_index=True)
    pivot = networks.pivot(index=['subreddit', 'window'], columns='variant', values='largest_component_pct')
    order = [(s, w) for s in ['marvelstudios', 'DC_Cinematic', 'PS5', 'xbox'] for w in ['sep', 'oct']]
    pivot = pivot.reindex(order)
    labels = [f"{dict(marvelstudios='Marvel', DC_Cinematic='DC', PS5='PS5', xbox='Xbox')[s]}  {w.title()}" for s, w in order]
    fig, ax = plt.subplots(figsize=(9.6, 3.1))
    y = np.arange(len(pivot))
    ax.hlines(y, pivot.comment_replies, pivot.all_replies, color='#c4cdd4', linewidth=3)
    ax.scatter(pivot.all_replies, y, color='#2563a6', s=40, label='All replies', zorder=3)
    ax.scatter(pivot.comment_replies, y, color='#c35b26', s=40, label='Comment replies only', zorder=3)
    for i, r in enumerate(pivot.itertuples()):
        ax.text(r.comment_replies - 1.2, i, f'{r.comment_replies:.1f}', ha='right', va='center', fontsize=9)
        ax.text(r.all_replies + .7, i, f'{r.all_replies:.1f}', ha='left', va='center', fontsize=9)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(45, 105)
    ax.set_xlabel('Accounts in the largest weak component (%)')
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.01), ncol=2, frameon=False)
    ax.spines[['top', 'right', 'left']].set_visible(False)
    ax.grid(axis='x', alpha=.15)
    fig.tight_layout()
    fig.savefig(assets / 'component_sensitivity.png', dpi=220, bbox_inches='tight')
    plt.close(fig)

    html = (REPORT / 'course_report.html').read_text(encoding='utf-8')
    counts = {}
    for key, tag in [('abstract', 'p'), ('introduction', 'div'), ('literature_a', 'div'), ('literature_b', 'div')]:
        match = re.search(fr'<{tag} id="{key}">(.*?)</{tag}>', html, re.S)
        counts[key] = len(plain(match.group(1)).split())
    counts['literature_total'] = counts['literature_a'] + counts['literature_b']
    assert counts['abstract'] <= 100, counts
    assert counts['introduction'] <= 300, counts
    assert 600 <= counts['literature_total'] <= 800, counts
    inventory = pd.read_csv(OUT / 'collection_inventory.csv')
    assert inventory.rows.sum() == 1168638 and inventory.valid_days.sum() == 336
    assert len(networks) == 16
    for pair, expected in [('superheroes', 8807), ('consoles', 4978)]:
        overlap = pd.read_csv(OUT / f'tables/{pair}_overlap.csv')
        assert overlap[(overlap.window == 'pooled_56d') & (overlap.min_comments == 1)].iloc[0].shared == expected
    literature = plain(re.search(r'<div id="literature_a">(.*?)<h1>Project objectives', html, re.S).group(1))
    assert set(map(int, re.findall(r'\[(\d+)\]', literature))) == set(range(1, 13))
    paths = [p for folder in ['src', 'tools', 'tests'] for p in (ROOT / folder).glob('*.py')]
    paths += list(ROOT.glob('*.py'))
    source_inventory = []
    for p in sorted(set(paths)):
        source = p.read_text(encoding='utf-8-sig')
        tree = ast.parse(source)
        source_inventory.append(dict(path=str(p.relative_to(ROOT)), lines=len(source.splitlines()),
            functions=[n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))],
            sha256=hashlib.sha256(source.encode()).hexdigest()))
    images = []
    for relative in re.findall(r'<img src="([^"]+)"', html):
        p = (REPORT / relative).resolve()
        assert p.is_file(), p
        images.append(dict(path=str(p.relative_to(ROOT)), sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    evidence = dict(word_counts=counts, recent_review_papers=12, total_research_references=14,
        archive_records=int(inventory.rows.sum()), daily_files=int(inventory.valid_days.sum()),
        network_variants=len(networks), figures=images, code_inventory=source_inventory,
        contribution_status='Proposed equal allocation; requires confirmation against actual work',
        report_source_sha256=hashlib.sha256(html.encode()).hexdigest())
    (REPORT / 'report_evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(counts))
    print(f'Verified {len(source_inventory)} Python files, {len(images)} figure images, and key report totals.')


if __name__ == '__main__':
    main()
