"""Check the delivered PowerPoint against its content and source tables."""
import csv
import hashlib
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'reports/presentation'
NS = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}


def normalize(value):
    return ' '.join(str(value).split())


def main():
    content = json.loads((FOLDER/'presentation_content.json').read_text(encoding='utf-8'))
    pptx = FOLDER/'Group6_FandomFaultLines_Presentation.pptx'
    records=[]
    with zipfile.ZipFile(pptx) as package:
        assert package.testzip() is None
        slide_paths=[p for p in package.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',p)]
        assert len(slide_paths)==35==content['slide_count']
        for index,spec in enumerate(content['slides'],1):
            slide=ET.fromstring(package.read(f'ppt/slides/slide{index}.xml'))
            notes=ET.fromstring(package.read(f'ppt/notesSlides/notesSlide{index}.xml'))
            visible=normalize(' '.join(t.text or '' for t in slide.findall('.//a:t',NS)))
            note_text=normalize(' '.join(t.text or '' for t in notes.findall('.//a:t',NS)))
            if not spec.get('cover'):
                assert normalize(spec['title']) in visible,(index,'title')
            assert normalize(spec['notes']) in note_text,(index,'notes')
            assert normalize(spec['source']) in note_text,(index,'sources')
            for element in spec['elements']:
                if element['type']=='text':
                    assert normalize(element['text']) in visible,(index,element['text'])
                elif element['type']=='table':
                    for cell in element['headers']+[c for row in element['rows'] for c in row]:
                        assert normalize(cell) in visible,(index,cell)
            records.append(dict(slide=index,title=spec['title'],
                                native_tables=len(slide.findall('.//a:tbl',NS)),
                                editable_shapes=len(slide.findall('.//p:sp',NS)),
                                images=len(slide.findall('.//p:pic',NS)),
                                notes_words=len(note_text.split())))
    with (ROOT/'outputs/study/tables/superheroes_sampling.csv').open() as f:
        sample=[float(r['jaccard_pct']) for r in csv.DictReader(f)
                if r['window']=='sep' and float(r['fraction'])==.1 and r['min_comments']=='1']
    mean=sum(sample)/len(sample)
    assert f'{mean:.2f}%'=='3.15%'
    assert f'{mean:.2f} percent' in content['slides'][9]['notes']
    assert content['slides'][9]['chart_data'][0]['series'][0]['values'][0]==mean
    assert all((ROOT/'logs/presentation_qa'/f'slide-{i:02d}.png').is_file() for i in range(1,36))
    result=dict(slides=35,main_slides=27,backup_slides=8,
                native_tables=sum(r['native_tables'] for r in records),
                notes_verified=35,sampling_mean_pct=mean,
                chart_editing='Bar charts use editable native shapes and text, with data in presentation_content.json.',
                package_sha256=hashlib.sha256(pptx.read_bytes()).hexdigest(),slide_details=records)
    (ROOT/'logs/presentation_qa/content_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='slide_details'},indent=2))


if __name__=='__main__':
    main()
