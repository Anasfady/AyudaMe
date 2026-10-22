"""Script de validación End-to-End para el RAG Pipeline con datos reales."""

import os
from dotenv import load_dotenv

# Cargar variables de entorno del .env ANTES de importar nada del proyecto
load_dotenv()

from src.rag.pipeline import RAGPipeline, get_llm
from src.retrieval.retriever import get_retriever


def run_e2e_demo():
    print("=" * 60)
    print("🚀 INICIANDO PRUEBA END-TO-END: ASESORIA RAG PIPELINE")
    print("=" * 60)

    # 1. Validamos los defaults V1 compartidos (k=8, threshold=0.82).
    print("\n[1/3] Conectando Retriever de ChromaDB...")
    retriever = get_retriever()

    # 2. Instanciamos el LLM configurado (get_llm ya lee internamente la configuración)
    print("\n[2/3] Conectando LLM Provider...")
    llm = get_llm()
    print(
        f"      Modelo cargado: {getattr(llm, 'model_name', getattr(llm, 'model', type(llm).__name__))}"
    )

    # 3. Inicializamos el pipeline
    print("\n[3/3] Inicializando RAGPipeline...")
    pipeline = RAGPipeline(retriever=retriever, llm=llm)

    # 4. Probamos dos consultas: una fiscal directa y una fuera de dominio
    queries = [
        "¿Cuándo se presenta el Modelo 303 del IVA?",
        "¿Qué tiempo hace hoy en Madrid?",
    ]

    for q in queries:
        print("\n" + "-" * 50)
        print(f"❓ PREGUNTA: {q}")
        print("-" * 50)

        result = pipeline.answer_query(q)

        print("\n💬 RESPUESTA DEL LLM:")
        print(result["answer"])

        print(f"\n📚 FUENTES RECUPERADAS ({len(result['source_documents'])}):")
        if not result["source_documents"]:
            print(
                "   (Ninguna fuente recuperada - umbral de score aplicado correctamente)"
            )
        for i, doc in enumerate(result["source_documents"], 1):
            src = doc.metadata.get("source", "Desconocido")
            p = doc.metadata.get("page", "N/A")
            pe = doc.metadata.get("page_end", p)
            p_str = f"Pág. {p}" if p == pe else f"Págs. {p}–{pe}"
            print(f"   [{i}] {src} ({p_str})")


if __name__ == "__main__":
    run_e2e_demo()
