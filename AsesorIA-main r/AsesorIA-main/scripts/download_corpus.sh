#!/usr/bin/env bash
#
# Usage:  bash scripts/download_corpus.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw

echo "Descargando manuales del IRPF 2025..."
curl -fL -o data/raw/ManualRenta2025Parte1_es_es.pdf \
  "https://sede.agenciatributaria.gob.es/static_files/Sede/Biblioteca/Manual/Practicos/IRPF/IRPF-2025/ManualRenta2025Parte1_es_es.pdf"
curl -fL -o data/raw/ManualRenta2025Parte2_es_es.pdf \
  "https://sede.agenciatributaria.gob.es/static_files/Sede/Biblioteca/Manual/Practicos/IRPF/IRPF-2025-Deducciones-autonomicas/ManualRenta2025Parte2_es_es.pdf"

echo "Descargando manual del IVA 2025..."
curl -fL -o data/raw/Manual_IVA_2025.pdf \
  "https://sede.agenciatributaria.gob.es/static_files/Sede/Biblioteca/Manual/Practicos/IVA/Manual_IVA_2025.pdf"

echo "Descargando legislación RETA..."
curl -fL -o data/raw/RDL_08_2015_LGSS.pdf \
  "https://www.boe.es/buscar/pdf/2015/BOE-A-2015-11724-consolidado.pdf"
curl -fL -o data/raw/LETA_20_2007.pdf \
  "https://www.boe.es/buscar/pdf/2007/BOE-A-2007-13409-consolidado.pdf"
curl -fL -o data/raw/RDL_13_2022_RegimenCotizacion_RETA.pdf \
  "https://www.boe.es/boe/dias/2022/07/27/pdfs/BOE-A-2022-12482.pdf"
curl -fL -o data/raw/PJC_178_2025_OrdenCotizacion_RETA.pdf \
  "https://www.boe.es/buscar/pdf/2025/BOE-A-2025-3780-consolidado.pdf"

echo "Verificando tamaños:"
ls -la data/raw/*.pdf 2>/dev/null || echo "  (aun no hay PDFs — ejecuta este script con conexión a internet)"
