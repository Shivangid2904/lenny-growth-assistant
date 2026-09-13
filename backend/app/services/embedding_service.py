import logging
from typing import List
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


from app.exceptions import OllamaUnavailableError, AppError


class EmbeddingError(AppError):
    """Base exception for embedding errors."""
    def __init__(self, message: str, code: str = "EMBEDDING_ERROR", status_code: int = 500):
        super().__init__(code=code, message=message, status_code=status_code)


class EmbeddingDimensionMismatchError(EmbeddingError):
    """Raised when returned embedding dimension does not match expected dimension."""
    def __init__(self, message: str):
        super().__init__(message=message, code="EMBEDDING_DIMENSION_MISMATCH", status_code=500)



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
        self._client = httpx.Client(timeout=self.timeout)

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
            response = self._client.post(url, json=payload)
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

    def embed_texts(self, texts: List[str], max_workers: int = 4) -> List[List[float]]:
        """Generate vector embeddings for a list of texts concurrently."""
        if not texts:
            return []
        if len(texts) == 1:
            return [self.embed_text(texts[0])]

        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            embeddings = list(executor.map(self.embed_text, texts))

        logger.info(
            "embedding_batch_completed",
            extra={"count": len(texts), "model": self.model},
        )
        return embeddings


embedding_service = EmbeddingService()

