"""Execution-only audit adapter. Does not rewrite application or frozen scripts."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import sys,os,json,runpy,sqlite3,platform,hashlib,importlib.metadata,traceback

script=Path(sys.argv[1]).resolve(); work=Path(sys.argv[sys.argv.index('--work-dir')+1]).resolve()
original_args=[str(script),*sys.argv[2:]]
counts=Counter(); started=datetime.now(timezone.utc).isoformat(); error=None; code=0
def profile(frame,event,arg):
    if event=='call':
        filename=frame.f_code.co_filename.replace('\\','/')
        name=frame.f_code.co_name
        if '/app/services/' in filename or name in ['deny_network','deny'] or ('run_extension_replay' in filename and name=='<lambda>') or ('reproduce_baseline' in filename and name=='<lambda>'):
            counts[filename.split('/')[-1]+':'+name]+=1
    return profile
sys.argv=original_args
sys.setprofile(profile)
try:
    runpy.run_path(str(script),run_name='__main__')
except SystemExit as e:
    code=e.code if isinstance(e.code,int) else (0 if e.code is None else 1)
except BaseException:
    error=traceback.format_exc();code=1
    print(error,file=sys.stderr)
finally:
    sys.setprofile(None)
    # Closing handles/checkpointing the NEW disposable store affects persistence
    # only. The same mechanism is already present in the extension runner.
    if 'app.database' in sys.modules:
        try: sys.modules['app.database'].engine.dispose()
        except Exception as e: error=(error or '')+'\nengine dispose: '+repr(e)
    snapshot={}
    dbpath=work/'disposable_runtime/replay.db'
    if dbpath.exists():
        try:
            with sqlite3.connect(dbpath) as con:
                con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            with sqlite3.connect('file:'+dbpath.as_posix()+'?mode=ro',uri=True) as con:
                con.row_factory=sqlite3.Row
                for table in ['documents','pages','occurrences','chunks']:
                    cols=[r[1] for r in con.execute('PRAGMA table_info('+table+')')]
                    omit={'text','image_path','stored_path','embedding','created_at','updated_at','processed_at','context','content'}
                    wanted=[c for c in cols if c not in omit]
                    if wanted: snapshot[table]=[dict(r) for r in con.execute('SELECT '+','.join(wanted)+' FROM '+table+' ORDER BY id')]
                snapshot['page_text_digests']=[{'document_id':r['document_id'],'page_number':r['page_number'],'sha256':hashlib.sha256(r['text'].encode('utf-8')).hexdigest(),'text_length':len(r['text']),'ocr_used':r['ocr_used']} for r in con.execute('SELECT document_id,page_number,text,ocr_used FROM pages ORDER BY document_id,page_number')]
                snapshot['occurrence_extractors']=[dict(r) for r in con.execute('SELECT extractor,COUNT(*) AS count FROM occurrences GROUP BY extractor')]
                snapshot['embedding_vectors_present']=con.execute('SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL').fetchone()[0]
        except Exception: error=(error or '')+'\n'+traceback.format_exc();code=1
    work.mkdir(parents=True,exist_ok=True)
    (work/'storage_audit.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'started_utc':started,'finished_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'os':platform.uname()._asdict(),'command':[sys.executable,'-X','utf8',str(Path(__file__).resolve()),*original_args],'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'exit_code':code,'error':error,'profile_calls':dict(sorted(counts.items())),'compatibility_adapter':'UTF-8 process mode; passive call tracing; dispose and WAL checkpoint of new storage only; no change to extraction or retrieval logic','no_claim_of_human_validation':True}
    (work/'execution_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
sys.exit(code)
