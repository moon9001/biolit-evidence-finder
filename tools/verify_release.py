"""Read-only integrity and retained-array checks; never reruns an experiment."""
from pathlib import Path, PurePosixPath
import argparse, csv, hashlib, json, sys

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();root=args.root.resolve()
    freeze=json.loads((root/'FREEZE.json').read_text())
    manifest=root/freeze['frozen_payload_manifest']
    assert hashlib.sha256(manifest.read_bytes()).hexdigest()==freeze['manifest_sha256'],'Manifest mismatch'
    rows=list(csv.DictReader(manifest.open(encoding='utf-8',newline='')))
    seen=set();counts={'source':0,'record':0}
    for row in rows:
        rel=PurePosixPath(row['repository_path'])
        assert not rel.is_absolute() and '..' not in rel.parts and '\\' not in str(rel) and ':' not in str(rel),'Unsafe path'
        assert str(rel).casefold() not in seen,'Duplicate path'
        seen.add(str(rel).casefold());p=root/str(rel)
        assert p.resolve().is_relative_to(root),'Path escapes root'
        b=p.read_bytes()
        assert len(b)==int(row['bytes']) and hashlib.sha256(b).hexdigest()==row['sha256'],str(rel)
        counts[row['kind']]+=1
    assert counts=={'source':57,'record':56},counts
    for group,kind in [('S2_frozen_source','source'),('records','record')]:
        actual={p.relative_to(root).as_posix() for p in (root/group).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.pyo']}
        expected={r['repository_path'] for r in rows if r['kind']==kind}
        assert actual==expected,{'extra':sorted(actual-expected),'missing':sorted(expected-actual)}
    def read(path):return json.loads((root/'records'/path).read_text(encoding='utf-8-sig'))
    comparisons=[];summaries=[]
    def compare(label,a,b,keys):
        for key in keys:comparisons.append({'comparison':label,'field':key,'equal':a[key]==b[key]})
    for sample in ['baseline','extension']:
        hist=read('historical/'+('baseline_reproduced_here.json' if sample=='baseline' else 'extension_run_1.json'))
        runs={};stores={}
        for rnd in ['a','b']:
            r=read('current/'+sample+'_'+rnd+'/reproduced_results.json')
            runs[rnd]=r;stores[rnd]=read('current/'+sample+'_'+rnd+'/storage_audit.json')
            compare(sample+'_'+rnd+' vs historical',r,hist,['queries','targets','pages','occurrence_offsets'])
        compare(sample+' current A vs B',runs['a'],runs['b'],['queries','targets','pages','occurrence_offsets'])
        compare(sample+' documents/pages/offsets A vs B',stores['a'],stores['b'],['documents','pages','occurrences','chunks','page_text_digests','occurrence_extractors','embedding_vectors_present'])
        r=runs['a'];t=r['targets']
        summaries.append({'sample':sample,'pages':len(r['pages']),'targets':len(t),'literal':sum(x['exact_selected_page_returned'] for x in t),'name_index':sum(x['scientific_selected_page_returned'] for x in t),'spans':len(r['occurrence_offsets'])})
    ca=read('current/extension_a/controls.json');cb=read('current/extension_b/controls.json');ch=read('historical/extension_controls_1.json')
    compare('extension controls A vs B',ca,cb,list(ca));compare('extension controls A vs historical',ca,ch,list(ca))
    assert len(comparisons)==60 and all(x['equal'] for x in comparisons),'Retained arrays differ'
    original=read('replay_comparison.json')
    assert [(x['comparison'],x['field'],x['equal']) for x in comparisons]==[(x['comparison'],x['field'],x['equal']) for x in original['comparisons']] and original['differences']==[],'Recorded comparisons differ'
    print(json.dumps({'source_files':counts['source'],'machine_records':counts['record'],'sha256_checks':len(rows),'retained_array_comparisons':len(comparisons),'differences':[],'separate_samples':summaries,'new_experiment_executed':False},indent=2))

if __name__=='__main__':
    try:main()
    except Exception as e:print('FAIL: '+str(e),file=sys.stderr);sys.exit(1)
