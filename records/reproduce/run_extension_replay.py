"""Replay the supplied descriptive cases without any model service or secret.

Only a new working directory is written. The reviewer source and existing
application stores are never used in place or changed.
"""
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import sys
import tempfile
import uuid

parser = argparse.ArgumentParser()
parser.add_argument('--source-dir', type=Path, required=True)
parser.add_argument('--input-file', type=Path, default=Path(__file__).with_name('extension_input_spec.json'))
parser.add_argument('--cached-pdf-dir', type=Path)
parser.add_argument('--dependency-dir', type=Path)
parser.add_argument('--work-dir', type=Path)
args = parser.parse_args()
spec = json.loads(args.input_file.read_text(encoding='utf-8'))
work = (args.work_dir or Path(tempfile.gettempdir()) / ('biolit_descriptive_replay_' + uuid.uuid4().hex[:10])).resolve()
if work.exists():
    raise RuntimeError('Choose a new working directory; existing data must not be reused')
work.mkdir(parents=True)
source = args.source_dir.resolve()
if not (source / 'backend' / 'app' / 'services' / 'search_service.py').exists():
    raise RuntimeError('Point --source-dir at the supplied prototype source root')
copy = work / 'prototype_copy'
shutil.copytree(source, copy, ignore=shutil.ignore_patterns('.env', '.git', 'data', '__pycache__', '.venv', 'node_modules'))
raw = work / 'public_inputs'
raw.mkdir()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


for item in spec['source_files']:
    destination = raw / (item['identifier'] + '.pdf')
    cached = args.cached_pdf_dir / destination.name if args.cached_pdf_dir else None
    if cached and cached.exists():
        shutil.copy2(cached, destination)
    else:
        with urlopen(Request(item['download_url'], headers={'User-Agent': 'Mozilla/5.0 (descriptive research replay)'}), timeout=180) as response, destination.open('wb') as out:
            shutil.copyfileobj(response, out)
    if sha(destination) != item['sha256']:
        raise RuntimeError('The public PDF differs from the recorded version; do not silently treat it as the same input')

for name in ['LLM_API_BASE_URL', 'LLM_API_KEY', 'EMBEDDING_API_BASE_URL',
             'EMBEDDING_API_KEY', 'DEEPSEEK_OCR_URL', 'DEEPSEEK_OCR_KEY']:
    os.environ[name] = ''
runtime = work / 'disposable_runtime'
os.environ['DATA_DIR'] = str(runtime)
os.environ['DB_PATH'] = str(runtime / 'replay.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + (runtime / 'replay.db').as_posix()
os.environ['PAGE_IMAGE_DPI'] = '24'
if args.dependency_dir:
    sys.path.insert(0, str(args.dependency_dir.resolve()))
sys.path.insert(0, str(copy / 'backend'))


def deny_network(*args, **kwargs):
    raise RuntimeError('No external service is permitted during the replay')


socket.socket.connect = deny_network
socket.create_connection = deny_network
import fitz
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Document, Occurrence, Page
from app.schemas import PageOut
from app.services import embedding_service, ocr_service, pdf_service, search_service

embedding_service.embed_texts = lambda texts: None
ocr_service.is_available = lambda: False
init_db()
grouped = defaultdict(list)
for page in spec['selected_pages']:
    grouped[page['identifier']].append(page)
mapping, observed_pages = {}, []
for identifier, pages in grouped.items():
    excerpt = settings.uploads_dir / (identifier + '_selected_pages.pdf')
    with fitz.open(raw / (identifier + '.pdf')) as src:
        dst, labels = fitz.open(), []
        for index, page in enumerate(pages):
            position = page['source_zero_based_sequence']
            original = src[position]
            if original.get_label() != page['original_pdf_label_metadata']:
                raise RuntimeError('A selected source page label differs from the recorded input')
            text = original.get_text('text')
            if hashlib.sha256(text.encode('utf-8')).hexdigest() != page['pdf_text_sha256']:
                raise RuntimeError('Text extraction differs; report the dependency or input change before comparing results')
            dst.insert_pdf(src, from_page=position, to_page=position)
            if original.get_label():
                labels.append({'startpage': index, 'prefix': original.get_label(), 'style': '', 'firstpagenum': 1})
        dst.set_metadata({'title': identifier + ' selected source pages', 'author': ''})
        if labels:
            dst.set_page_labels(labels)
        dst.save(excerpt)
        dst.close()
    db = SessionLocal()
    doc = pdf_service.init_document(db, excerpt.name, excerpt)
    doc_id = doc.id
    db.close()
    pdf_service.process_document(doc_id, use_llm=False)
    db = SessionLocal()
    doc = db.get(Document, doc_id)
    if doc.status != 'completed':
        raise RuntimeError('Selected-page processing did not complete')
    for index, reference in enumerate(pages, 1):
        mapping[(doc_id, index)] = reference
    db.close()

queries, targets, offsets = [], [], []
db = SessionLocal()
try:
    for p in db.query(Page).order_by(Page.document_id, Page.page_number).all():
        reference = mapping[(p.document_id, p.page_number)]
        observed_pages.append({'candidate_id': reference['candidate_id'], 'label': p.page_label,
                               'label_preserved': p.page_label == reference['original_pdf_label_metadata'],
                               'page_detail_label_present': PageOut.model_validate(p).page_label == reference['original_pdf_label_metadata']})
    for o in db.query(Occurrence).filter(Occurrence.term_type.in_(['scientific_name', 'scientific_name_abbrev'])).all():
        p = db.get(Page, o.page_id)
        reference = mapping[(o.document_id, p.page_number)]
        offsets.append({'candidate_id': reference['candidate_id'], 'term': o.term, 'term_type': o.term_type,
                        'start': o.start_char, 'end': o.end_char,
                        'span_matches_normalized_term': re.sub(r'\s+', ' ', p.text[o.start_char:o.end_char]).strip() == o.term})
    for query in spec['query_strings']:
        for mode in ['exact', 'scientific']:
            results, _ = search_service.search(db, query, mode, limit=1000)
            queries.append({'query': query, 'mode': mode, 'result_count': len(results),
                            'unique_selected_pages': sorted({mapping[(r.document_id, r.page_number)]['candidate_id'] for r in results}),
                            'result_label_fields_present': sum('page_label' in r.model_dump() for r in results),
                            'selected_hits': [{'candidate_id': mapping[(r.document_id,r.page_number)]['candidate_id'], 'matched_term': r.matched_term, 'score': r.score} for r in results]})
    for anchor in spec['target_anchors']:
        record = {'candidate_id': anchor['candidate_id'], 'target_query': anchor['target_query']}
        for mode in ['exact', 'scientific']:
            query = next(q for q in queries if q['query'] == anchor['target_query'] and q['mode'] == mode)
            record[mode + '_selected_page_returned'] = anchor['candidate_id'] in query['unique_selected_pages']
        targets.append(record)
finally:
    db.close()

expected = spec['expected_target_results']
agreement = None if expected is None else all(all(record[key] == expected[index][key] for key in ['candidate_id', 'target_query', 'exact_selected_page_returned', 'scientific_selected_page_returned'])
                for index, record in enumerate(targets))
result = {'run_at_utc': datetime.now(timezone.utc).isoformat(),
          'sample': spec.get('sample_description', 'selected public pages'),
          'selection': spec.get('selection', 'descriptive selected pages'),
          'prototype_logic_modified': False, 'human_or_expert_participation': False,
          'external_provider_calls': False, 'queries': queries, 'targets': targets,
          'pages': observed_pages, 'occurrence_offsets': offsets,
          'agrees_with_reported_selected_targets': agreement,
          'interpretation': 'locator and string-handling conformance only; not precision, recall, taxonomic validation or user benefit'}
(work / 'reproduced_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
# Run controls against the complete current store before closing this process.
# A separate read of a partially persisted temporary store must never masquerade
# as a valid control. The control script checks all page and target records.
import runpy
previous_argv = sys.argv
try:
    sys.argv = [str(Path(__file__).with_name('check_controls.py')), '--run-dir', str(work),
                '--spec', str(args.input_file.resolve())]
    if args.dependency_dir:
        sys.argv += ['--dependency-dir', str(args.dependency_dir.resolve())]
    runpy.run_path(Path(__file__).with_name('check_controls.py'), run_name='__main__')
finally:
    sys.argv = previous_argv
# Close pooled handles and checkpoint the disposable SQLite store before exit.
# This affects evidence persistence only, never extraction or query behavior.
from app.database import engine
engine.dispose()
import sqlite3
with sqlite3.connect(runtime / 'replay.db') as connection:
    connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    persisted_pages = connection.execute('SELECT COUNT(*) FROM pages').fetchone()[0]
if persisted_pages != len(observed_pages):
    raise RuntimeError('Disposable store persistence differs from the recorded in-memory page count')
print('Selected pages:', len(observed_pages), 'selected anchors:', len(targets))
print('Literal target pages returned:', sum(r['exact_selected_page_returned'] for r in targets), '/', len(targets))
print('Name-index target pages returned:', sum(r['scientific_selected_page_returned'] for r in targets), '/', len(targets))
print('Agreement with recorded target results:', agreement)
sys.exit(2 if agreement is False else 0)
