"""Native Gephi projects for reviewed second-window combined reply layers."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd

from build_gephi import ROOT, JAR, EXPECTED_SHA256


def main():
    if hashlib.sha256(JAR.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise ValueError('Unexpected Gephi toolkit checksum')
    source = ROOT / 'tools/GephiStudy.java'
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(JAR),str(source)],check=True)
    out = ROOT / 'outputs/study'
    rows = pd.read_csv(out/'network_review/combined_exports.csv')
    results=[]
    for r in rows.itertuples():
        stem=f'combined_{r.pair}_{r.window}_{r.variant}'
        full,focus=(out/'networks'/(stem+suffix) for suffix in ['_full.gexf','_focus.gexf'])
        native=out/'networks'/(stem+'_native')
        validation=Path(str(native)+'_validation.json')
        digest=hashlib.sha256(full.read_bytes()+focus.read_bytes()+source.read_bytes()).hexdigest()
        previous=json.loads(validation.read_text()) if validation.exists() else {}
        if previous.get('source_sha256') != digest or not Path(str(native)+'.gephi').exists():
            print('GEPHI',stem,flush=True)
            subprocess.run(['java','-Xmx3g','-Djava.awt.headless=true','-cp',str(JAR)+(';' if sys.platform=='win32' else ':')+str(ROOT/'tools'),
                'GephiStudy',str(full),str(focus),str(native),str(r.full_nodes),str(r.full_edges),str(r.full_reply_events)],check=True)
            previous=json.loads(validation.read_text())
            previous['source_sha256']=digest
            validation.write_text(json.dumps(previous,indent=2))
        (out/'figures'/f'gephi_{stem}.png').write_bytes(Path(str(native)+'.png').read_bytes())
        results.append(dict(pair=r.pair,window=r.window,variant=r.variant,**previous))
    pd.DataFrame(results).to_csv(out/'network_review/gephi_validation.csv',index=False)


if __name__=='__main__':
    main()
