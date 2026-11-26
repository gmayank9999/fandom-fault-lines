"""Render the Word-exported PDF and check the delivered report structure."""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--render-dependencies', type=Path)
    args = parser.parse_args()
    if args.render_dependencies:
        sys.path.insert(0, str(args.render_dependencies.resolve()))
    import pymupdf as fitz
    folder = ROOT / 'reports'
    qa = ROOT / 'logs/course_report_qa'
    qa.mkdir(parents=True, exist_ok=True)
    pdf = fitz.open(folder / 'Group6_FandomFaultLines_Report.pdf')
    pages = []
    for i, page in enumerate(pdf):
        text = page.get_text()
        page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(qa / f'page-{i+1:02d}.png')
        pages.append(dict(page=i+1, words=len(text.split()), images=len(page.get_images()),
                          first_lines=text.splitlines()[:4]))
    text = '\n'.join(p.get_text() for p in pdf)
    (qa / 'report_extracted.txt').write_text(text, encoding='utf-8')
    for token in ['Mayank Gupta', '230553', 'Anurag Kumar', '230616', 'Jhalak Kapila', '230576',
                  '1,168,638', '8,807', '4,978', '61,356', 'proposed equal allocation']:
        assert token in text, token
    assert '\ufffd' not in text
    assert len(pdf) >= 12
    with zipfile.ZipFile(folder / 'Group6_FandomFaultLines_Report.docx') as archive:
        media = [name for name in archive.namelist() if name.startswith('word/media/')]
        assert len(media) >= 8, len(media)
        ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        xml = ET.fromstring(archive.read('word/document.xml'))
        docxtext = ' '.join(x.text or '' for x in xml.findall('.//w:t',ns))
        assert 'Group 6' in docxtext
        core = archive.read('docProps/core.xml').decode()
        assert all(n in core for n in ['Mayank Gupta', 'Anurag Kumar', 'Jhalak Kapila'])
    result = dict(pages=pages, page_count=len(pdf), embedded_images=len(media),
                  status='Structural checks passed; page PNGs require visual inspection')
    (qa / 'checks.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
