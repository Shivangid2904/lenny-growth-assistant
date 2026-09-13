import logging
from typing import List
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Base exception for embedding errors."""
    pass


class OllamaUnavailableError(EmbeddingError):
    """Raised when Ollama embedding service is unreachable or errors."""
    pass


class EmbeddingDimensionMismatchError(EmbeddingError):
    """Raised when returned embedding dimension does not match expected dimension."""
    pass


class EmbeddingService:
    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        expected_dim: int = None,
        timeout: float = 30.0,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_embedding_model or settings.embedding_model
        self.expected_dim = expected_dim or settings.embedding_dimension
        self.timeout = timeout

    def embed_text(self, text: str) -> List[float]:
        """Generate a 768-dim vector embedding for a single text chunk."""
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text.")

        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text,
        }

        try:
            response = httpx.post(url, json=payload, timeout=self.timeout)
        except Exception as exc:
            logger.error("ollama_unavailable", extra={"error": str(exc), "url": url})
            raise OllamaUnavailableError(
                f"Ollama is unreachable at '{self.base_url}'. Ensure Ollama is running and model '{self.model}' is pulled."
            ) from exc

        if response.status_code != 200:
            logger.error(
                "ollama_unavailable",
                extra={"status_code": response.status_code, "body": response.text},
            )
            raise OllamaUnavailableError(
                f"Ollama returned status {response.status_code}: {response.text}"
            )

        data = response.json()
        embedding = data.get("embedding")
        if not embedding or not isinstance(embedding, list):
            raise OllamaUnavailableError("Ollama response did not contain a valid 'embedding' array.")

        if len(embedding) != self.expected_dim:
            logger.error(
                "embedding_dimension_mismatch",
                extra={"expected": self.expected_dim, "actual": len(embedding)},
            )
            raise EmbeddingDimensionMismatchError(
                f"Embedding dimension mismatch: expected {self.expected_dim}, got {len(embedding)}"
            )

        return embedding

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a list of texts sequentially."""
        embeddings = []
        for i, t in enumerate(texts):
            embeddings.append(self.embed_text(t))
        logger.info(
            "embedding_batch_completed",
            extra={"count": len(texts), "model": self.model},
        )
        return embeddings


embedding_service = EmbeddingService()
