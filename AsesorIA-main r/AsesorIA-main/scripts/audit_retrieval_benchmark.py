"""Auditoría estructural del benchmark; no calcula métricas de retrieval."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from pypdf import PdfReader
from src.common.settings import PROJECT_ROOT


def main():
    raw = (PROJECT_ROOT / 'data/eval/benchmark.json').read_bytes()
    questions = json.loads(raw)['questions']  # Acepta el BOM UTF-16 del archivo actual.
    with (PROJECT_ROOT / 'data/sources.csv').open(encoding='utf-8-sig', newline='') as handle:
        sources = list(csv.DictReader(handle))
    assert len({q['id'] for q in questions}) == len(questions), 'IDs de preguntas duplicados'
    assert len({s['doc_id'] for s in sources}) == len(sources), 'doc_id duplicados'
    documents = {}
    for source in sources:
        path = PROJECT_ROOT / 'data/raw' / source['filename']
        reader = PdfReader(path)
        references = [q for q in questions if q.get('expected_doc_id') == source['doc_id']]
        page_numbers = sorted({q['expected_page'] for q in references if 'expected_page' in q})
        for number in page_numbers:
            assert type(number) is int and 1 <= number <= len(reader.pages)
        documents[source['doc_id']] = dict(
            filename=source['filename'], pages=len(reader.pages),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            questions=[q['id'] for q in references],
            referenced_pages=[dict(page=n, excerpt=(reader.pages[n-1].extract_text() or '')[:500],
                                   footer=(reader.pages[n-1].extract_text() or '')[-250:])
                              for n in page_numbers])
    for q in questions:
        if 'expected_doc_id' in q:
            assert q['expected_doc_id'] in documents, f"Documento desconocido: {q['id']}"
    report = dict(benchmark_sha256=hashlib.sha256(raw).hexdigest(), questions=len(questions),
                  categories=dict(Counter(q['category'] for q in questions)),
                  document_reference_count=sum('expected_doc_id' in q for q in questions),
                  page_reference_count=sum('expected_page' in q for q in questions),
                  missing_pages=[q['id'] for q in questions if 'expected_doc_id' in q and 'expected_page' not in q],
                  documents=documents,
                  limitation='Page bounds and excerpts only; not validation of complete answer evidence.')
    output = PROJECT_ROOT / 'chroma_db/benchmark_audit.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'documents'}, ensure_ascii=True, indent=2))
    print('Report:', output)


if __name__ == '__main__':
    main()
