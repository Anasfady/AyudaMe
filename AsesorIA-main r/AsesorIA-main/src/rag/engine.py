"""
Módulo motor (Engine) para AsesorIA.
Proporciona la interfaz de alto nivel para interactuar con el sistema RAG,
gestionando la instanciación única (Singleton/Factory) y el formato estándar de salida.
"""

from typing import Any, Dict, Optional
from src.common.settings import DEFAULT_TOP_K, DEFAULT_SCORE_THRESHOLD
from src.rag.pipeline import RAGPipeline, get_llm
from src.retrieval.retriever import get_retriever


class RAGEngine:
    """
    Fachada principal para el consumo del pipeline RAG.
    Diseñada para ser consumida de forma directa por endpoints de FastAPI,
    interfaces de usuario (Streamlit) o scripts de evaluación.
    """

    def __init__(
        self,
        top_k: int = DEFAULT_TOP_K,
        score_threshold: Optional[float] = DEFAULT_SCORE_THRESHOLD,
        pipeline: Optional[RAGPipeline] = None,
    ):
        if pipeline is not None:
            self.pipeline = pipeline
        else:
            retriever = get_retriever(top_k=top_k, score_threshold=score_threshold)
            llm = get_llm()
            self.pipeline = RAGPipeline(retriever=retriever, llm=llm)

    def query(self, question: str) -> Dict[str, Any]:
        """
        Procesa una consulta de usuario a través del pipeline.

        Retorna un diccionario estructurado:
        - question (str): Pregunta original formulada.
        - answer (str): Respuesta generada por el modelo.
        - sources (list[dict]): Lista estructurada de metadatos de las fuentes usadas.
        - metrics (dict): Tiempos de latencia (retrieval, generation, total).
        - raw_documents (list): Documentos LangChain originales recuperados.
        """
        clean_question = question.strip()
        if not clean_question:
            return {
                "question": question,
                "answer": "La consulta no puede estar vacía.",
                "sources": [],
                "metrics": {
                    "retrieval_latency_s": 0.0,
                    "generation_latency_s": 0.0,
                    "total_latency_s": 0.0,
                },
                "raw_documents": [],
            }

        result = self.pipeline.answer_query(clean_question)
        source_docs = result.get("source_documents", [])
        metrics = result.get("metrics", {})

        # Formateo amigable de fuentes para la API/UI
        formatted_sources = []
        for doc in source_docs:
            metadata = doc.metadata or {}
            source = metadata.get("source", "Documento desconocido")
            page_start = metadata.get("page")
            page_end = metadata.get("page_end", page_start)

            if page_start is not None:
                if page_end is not None and page_end != page_start:
                    page_label = f"Págs. {page_start}–{page_end}"
                else:
                    page_label = f"Pág. {page_start}"
            else:
                page_label = "Pág. N/A"

            formatted_sources.append(
                {
                    "source": source,
                    "page": page_label,
                    "snippet": doc.page_content[:200]
                    + ("..." if len(doc.page_content) > 200 else ""),
                }
            )

        return {
            "question": clean_question,
            "answer": result.get("answer", ""),
            "sources": formatted_sources,
            "metrics": metrics,
            "latency_ms": round(metrics.get("total_latency_s", 0.0) * 1000, 2),
            "raw_documents": source_docs,
        }


# Instancia singleton para reutilización global
_engine_instance: Optional[RAGEngine] = None


def get_rag_engine(
    top_k: int = DEFAULT_TOP_K, score_threshold: Optional[float] = DEFAULT_SCORE_THRESHOLD
) -> RAGEngine:
    """Retorna una instancia reutilizable del RAGEngine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RAGEngine(top_k=top_k, score_threshold=score_threshold)
    return _engine_instance
