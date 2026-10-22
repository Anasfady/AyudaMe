"""
Pruebas unitarias para validar las plantillas de prompts de AsesorIA.
"""

import pytest
from src.retrieval.prompts import CHAT_QA_PROMPT, STANDALONE_QA_PROMPT, SYSTEM_PROMPT
from unittest.mock import MagicMock
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from src.rag.pipeline import RAGPipeline, format_docs
from langchain_core.language_models.fake_chat_models import FakeListChatModel


def test_system_prompt_contains_critical_rules():
    """Verifica que el prompt de sistema contenga las directrices clave."""
    assert "Grounding estricto" in SYSTEM_PROMPT
    assert "Mitigación de alucinaciones" in SYSTEM_PROMPT
    assert "Trazabilidad y citas" in SYSTEM_PROMPT
    assert "No dispongo de suficiente información" in SYSTEM_PROMPT


def test_chat_qa_prompt_formatting():
    """Verifica la correcta inyección de variables en ChatPromptTemplate."""
    dummy_context = "El Modelo 303 de IVA se presenta de forma trimestral."
    dummy_question = "¿Cuándo se presenta el IVA?"

    formatted_messages = CHAT_QA_PROMPT.format_messages(
        context=dummy_context, question=dummy_question
    )

    # Debe generar 2 mensajes: system y human
    assert len(formatted_messages) == 2
    assert formatted_messages[0].type == "system"
    assert formatted_messages[1].type == "human"

    # El contenido debe incluir el contexto y la pregunta inyectados
    assert dummy_context in formatted_messages[1].content
    assert dummy_question in formatted_messages[1].content


def test_standalone_qa_prompt_formatting():
    """Verifica la correcta inyección de variables en el prompt estándar."""
    dummy_context = "Los gastos de manutención tienen un límite de 26,67 € diarios."
    dummy_question = "¿Cuánto puedo desgravar de comidas?"

    formatted_text = STANDALONE_QA_PROMPT.format(
        context=dummy_context, question=dummy_question
    )

    assert dummy_context in formatted_text
    assert dummy_question in formatted_text
    assert "RESPUESTA:" in formatted_text


def test_format_docs_with_metadata():
    """Valida que format_docs incluya el texto, la fuente y la página."""
    sample_docs = [
        Document(
            page_content="Contenido sobre IVA trimestral.",
            metadata={"source": "manual_iva.pdf", "page": 12},
        ),
        Document(
            page_content="Contenido sobre IRPF.",
            metadata={"source": "manual_irpf.pdf", "page": 4},
        ),
    ]

    formatted_text = format_docs(sample_docs)

    assert "[Fragmento 1] - Fuente: manual_iva.pdf (Pág. 12)" in formatted_text
    assert "Contenido sobre IVA trimestral." in formatted_text
    assert "[Fragmento 2] - Fuente: manual_irpf.pdf (Pág. 4)" in formatted_text


def test_format_docs_empty():
    """Valida el comportamiento cuando la lista de documentos recuperados está vacía."""
    assert format_docs([]) == "No se encontraron documentos relevantes."


def test_rag_pipeline_answer_query():
    """Valida el flujo completo de answer_query con un retriever simulado y un Fake LLM."""
    # 1. Mock del Retriever
    mock_retriever = MagicMock()
    mock_docs = [
        Document(
            page_content="El plazo límite del Modelo 303 es el 20 del mes posterior al trimestre.",
            metadata={"source": "calendario_aeat.pdf", "page": 2},
        )
    ]
    mock_retriever.invoke.return_value = mock_docs

    # 2. Fake LLM nativo de LangChain (hereda de BaseChatModel y cumple la validación Pydantic)
    expected_response = "El Modelo 303 debe presentarse hasta el día 20."
    fake_llm = FakeListChatModel(responses=[expected_response])

    # 3. Instanciar y ejecutar el pipeline
    pipeline = RAGPipeline(retriever=mock_retriever, llm=fake_llm)
    result = pipeline.answer_query("¿Cuándo se presenta el Modelo 303?")

    # 4. Aserciones
    assert "answer" in result
    assert "source_documents" in result
    assert result["answer"] == expected_response
    assert len(result["source_documents"]) == 1
    assert result["source_documents"][0].metadata["source"] == "calendario_aeat.pdf"
