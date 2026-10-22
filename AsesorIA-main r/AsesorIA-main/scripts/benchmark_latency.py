"""Script de benchmarking para medir tiempos de respuesta y rendimiento del RAG Engine."""

import os
from dotenv import load_dotenv

load_dotenv()

from src.rag.engine import get_rag_engine


def run_benchmark():
    print("=" * 65)
    print("⏱️  BENCHMARK DE TIEMPOS DE RESPUESTA - ASESORIA RAG ENGINE")
    print("=" * 65)

    engine = get_rag_engine()

    test_queries = [
        "¿Cuándo se presenta el Modelo 303 del IVA?",
        "¿Qué deducciones autonómicas existen en Madrid?",
        "¿Cuáles son los plazos para el Modelo 130 de IRPF?",
    ]

    total_pipeline_times = []

    for i, q in enumerate(test_queries, start=1):
        print(f"\n[Test {i}/{len(test_queries)}] Pregunta: {q}")
        res = engine.query(q)

        m = res.get("metrics", {})
        t_ret = m.get("retrieval_latency_s", 0.0)
        t_gen = m.get("generation_latency_s", 0.0)
        t_tot = m.get("total_latency_s", 0.0)

        total_pipeline_times.append(t_tot)

        print(f"  ├── Latencia Retrieval (ChromaDB) : {t_ret:.3f} s")
        print(f"  ├── Latencia Generación (LLM)     : {t_gen:.3f} s")
        print(f"  └── Latencia Total                : {t_tot:.3f} s")
        print(f"  Recuperadas: {len(res['sources'])} fuentes | Respuesta: {res['answer'][:80]}...")

    avg_time = sum(total_pipeline_times) / len(total_pipeline_times)
    print("\n" + "=" * 65)
    print(f"📊 RESUMEN: Latencia media del Engine = {avg_time:.3f} s")
    print("=" * 65)


if __name__ == "__main__":
    run_benchmark()