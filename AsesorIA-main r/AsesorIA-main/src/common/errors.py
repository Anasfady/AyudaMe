"""Custom exceptions shared across modules."""


class UnreadableDocumentError(Exception):
    """Raised when a document has no extractable text (e.g. a scanned PDF)."""


class UnsupportedFileTypeError(Exception):
    """Raised when the file extension is not PDF, TXT or Markdown."""


class LLMProviderError(Exception):
    """Raised when the LLM provider fails or times out."""
