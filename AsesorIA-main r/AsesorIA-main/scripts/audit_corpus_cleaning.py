"""Registra las líneas que elimina la limpieza, sin cambiarla ni indexar datos."""
import csv
import hashlib
import json
from collections import Counter
from src.common.settings import PROJECT_ROOT
from src.ingestion.loaders import load_document
from src.ingestion.cleaning import clean_text, remove_repeated_lines


def main():
    with (PROJECT_ROOT / 'data/sources.csv').open(encoding='utf-8-sig', newline='') as handle:
        sources = list(csv.DictReader(handle))
    report = []
    for source in sources:
        print('Revisando ' + source['doc_id'], flush=True)
        path = PROJECT_ROOT / 'data/raw' / source['filename']
        pages = load_document(path)
        processed = remove_repeated_lines(pages)
        assert [p.page for p in pages] == [p.page for p in processed]
        removed, examples = Counter(), {}
        for before, after in zip(pages, processed, strict=True):
            difference = Counter(before.text.splitlines()) - Counter(after.text.splitlines())
            removed.update(difference)
            for line in difference:
                examples.setdefault(line, [])
                if len(examples[line]) < 3:
                    examples[line].append(before.page)
        row = dict(doc_id=source['doc_id'], filename=source['filename'],
                   sha256=hashlib.sha256(path.read_bytes()).hexdigest(), pages=len(pages),
                   removed_occurrences=sum(removed.values()),
                   empty_after_dedup=[a.page for b,a in zip(pages,processed) if b.text.strip() and not a.text.strip()],
                   empty_after_clean_text=[p.page for p in pages if p.text.strip() and not clean_text(p.text).strip()],
                   removed=[dict(line=line, count=count, example_pages=examples[line])
                            for line,count in removed.most_common()])
        report.append(row)
        print(json.dumps({k:v for k,v in row.items() if k != 'removed'},ensure_ascii=True), flush=True)
        print('Primeras líneas eliminadas:', json.dumps(row['removed'][:8],ensure_ascii=True), flush=True)
    output = PROJECT_ROOT / 'chroma_db/cleaning_audit.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Informe:', output)


if __name__ == '__main__':
    main()
