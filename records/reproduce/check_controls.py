"""Read-only controls on a newly created replay store; no original data is touched."""
from pathlib import Path
from collections import Counter
import argparse,json,os,socket,sys,re

p=argparse.ArgumentParser()
p.add_argument('--run-dir',type=Path,required=True)
p.add_argument('--dependency-dir',type=Path)
p.add_argument('--spec',type=Path,default=Path(__file__).with_name('extension_input_spec.json'))
a=p.parse_args();run=a.run_dir.resolve()
spec=json.loads(a.spec.read_text());result=json.loads((run/'reproduced_results.json').read_text())
for name in ['LLM_API_BASE_URL','LLM_API_KEY','EMBEDDING_API_BASE_URL','EMBEDDING_API_KEY','DEEPSEEK_OCR_URL','DEEPSEEK_OCR_KEY']:os.environ[name]=''
os.environ['DATA_DIR']=str(run/'disposable_runtime')
os.environ['DB_PATH']=str(run/'disposable_runtime/replay.db')
os.environ['DATABASE_URL']='sqlite:///'+(run/'disposable_runtime/replay.db').as_posix()
if a.dependency_dir:sys.path.insert(0,str(a.dependency_dir.resolve()))
sys.path.insert(0,str(run/'prototype_copy/backend'))
def deny(*args,**kwargs):raise RuntimeError('No network during controls')
socket.socket.connect=deny;socket.create_connection=deny
from app.database import SessionLocal
from app.models import Page,Occurrence
from app.services import search_service

db=SessionLocal();mapping={}
for docid,ident in enumerate(dict.fromkeys(p['identifier'] for p in spec['selected_pages']),1):
 for n,r in enumerate([p for p in spec['selected_pages'] if p['identifier']==ident],1):mapping[(docid,n)]=r['candidate_id']
def hits(q,mode):
 rows,_=search_service.search(db,q,mode,limit=1000)
 return sorted((mapping[(r.document_id,r.page_number)],r.matched_term.lower()) for r in rows)
try:
 pages=db.query(Page).all()
 if len(pages)!=len(spec['selected_pages']):
  raise RuntimeError('Incomplete disposable store; control results must not be reported')
 for target in result['targets']:
  for mode in ['exact','scientific']:
   returned=any(cid==target['candidate_id'] for cid,term in hits(target['target_query'],mode))
   if returned!=target[mode+'_selected_page_returned']:
    raise RuntimeError('Control input differs from the recorded target output')
 alltext='\n'.join(p.text for p in pages).lower()
 absent=[]
 for q in ['Zznotpresentus qzxnever','Zzabsentgenus qzxabsent']:
  assert q.lower() not in alltext
  counts={mode:len(hits(q,mode)) for mode in ['exact','scientific']}
  absent.append({'query':q,'absent_in_selected_text':True,'counts':counts,'zero_results':all(v==0 for v in counts.values())})
 cases=[]
 for q in spec['query_strings']:
  for mode in ['exact','scientific']:
   ref=hits(q,mode)
   cases.append({'query':q,'mode':mode,'lowercase_agrees':ref==hits(q.lower(),mode),'uppercase_agrees':ref==hits(q.upper(),mode)})
 occurrences=db.query(Occurrence).filter(Occurrence.term_type.in_(['scientific_name','scientific_name_abbrev'])).all()
 repeated=Counter((o.document_id,o.page_id,o.term) for o in occurrences)
 groups=[]
 for (docid,pid,term),n in sorted(repeated.items()):
  if n<2:continue
  page=db.get(Page,pid);rows,_=search_service.search(db,term,'scientific',limit=1000)
  matching=[r for r in rows if r.document_id==docid and r.page_number==page.page_number and r.matched_term==term]
  groups.append({'candidate_id':mapping[(docid,page.page_number)],'term':term,'stored_occurrences':n,'returned_groups':len(matching),'one_group':len(matching)==1})
 sem,semnote=search_service.search(db,spec['query_strings'][0],'semantic',limit=1000)
 hybrid,note=search_service.search(db,spec['query_strings'][0],'hybrid',limit=1000)
 representations=[]
 for q,cid in [('Spiræa pubescens','N04'),('Spiræa chinensis','N04'),('Padus acro-\nphylla','N08'),('Padus acro- \nphylla','N08')]:
  representations.append({'query':q,'candidate_id':cid,'exact_page_returned':any(c==cid for c,t in hits(q,'exact')),'scientific_page_returned':any(c==cid for c,t in hits(q,'scientific')),'purpose':'Post hoc source-form diagnostic; excluded from the frozen 35-anchor denominator'})
 output={'selected_pages_checked':len(pages),'selected_anchors_rechecked':len(result['targets']),
         'negative_controls':absent,'query_case_controls':cases,'repeated_occurrence_groups':groups,
         'source_form_diagnostics':representations,
         'semantic_without_embeddings':{'result_count':len(sem),'note':semnote},
         'hybrid_without_embeddings':{'result_count':len(hybrid),'note':note},
         'network_blocked':True,'retrieval_or_extraction_logic_modified':False,
         'interpretation':'Software controls within fixed selected input; not evidence of calibrated probabilities, global search quality, or human judgment.'}
 (run/'controls.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
 print('Negative controls',all(x['zero_results'] for x in absent),'case checks',len(cases),all(x['lowercase_agrees'] and x['uppercase_agrees'] for x in cases),'multiple-occurrence groups',len(groups),all(x['one_group'] for x in groups))
 print('Semantic no-vector results',len(sem),'note',semnote)
finally:db.close()
