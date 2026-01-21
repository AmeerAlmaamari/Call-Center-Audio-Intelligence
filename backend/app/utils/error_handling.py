"""
Error handling utilities with retry logic and validation.
"""
import asyncio
import logging
import functools
from typing import TypeVar, Callable, Any, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, message: str, status_code: int = 500, retryable: bool = False):
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        super().__init__(self.message)


class RateLimitError(APIError):
    """Rate limit exceeded error."""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(message, status_code=429, retryable=True)


class TranscriptionError(APIError):
    """Transcription service error."""
    pass


class AnalysisError(APIError):
    """Analysis service error."""
    pass


class AudioValidationError(APIError):
    """Invalid audio file error."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400, retryable=False)


async def retry_with_backoff(
    func: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (httpx.HTTPStatusError, httpx.TimeoutException, RateLimitError),
    **kwargs
) -> T:
    """
    Execute an async function with exponential backoff retry logic.
    
    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exceptions that should trigger a retry
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e
            
            if attempt == max_retries:
                logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                raise
            
            # Check for rate limit with retry-after header
            delay = base_delay * (exponential_base ** attempt)
            if isinstance(e, RateLimitError) and e.retry_after:
                delay = e.retry_after
            elif isinstance(e, httpx.HTTPStatusError):
                if e.response.status_code == 429:
                    retry_after = e.response.headers.get("retry-after")
                    if retry_after:
                        delay = int(retry_after)
                elif e.response.status_code not in (429, 500, 502, 503, 504):
                    # Non-retryable HTTP error
                    raise
            
            delay = min(delay, max_delay)
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}. "
                f"Retrying in {delay:.1f}s. Error: {e}"
            )
            await asyncio.sleep(delay)
    
    raise last_exception


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
):
    """Decorator to add retry logic to async functions."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_with_backoff(
                func, *args,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                **kwargs
            )
        return wrapper
    return decorator


class AudioValidator:
    """Validate audio files for processing."""
    
    SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".mp4", ".aac"}
    MIN_DURATION_SECONDS = 1.0
    MAX_DURATION_SECONDS = 3600.0  # 1 hour
    MAX_FILE_SIZE_MB = 100
    MIN_FILE_SIZE_BYTES = 1000  # 1KB minimum
    
    @classmethod
    def validate_file_extension(cls, filename: str) -> bool:
        """Check if file has a supported audio extension."""
        from pathlib import Path
        ext = Path(filename).suffix.lower()
        return ext in cls.SUPPORTED_FORMATS
    
    @classmethod
    def validate_file_size(cls, file_size_bytes: int) -> tuple[bool, str]:
        """Validate file size is within acceptable range."""
        if file_size_bytes < cls.MIN_FILE_SIZE_BYTES:
            return False, f"File too small ({file_size_bytes} bytes). Minimum size is {cls.MIN_FILE_SIZE_BYTES} bytes."
        
        max_bytes = cls.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size_bytes > max_bytes:
            return False, f"File too large ({file_size_bytes / 1024 / 1024:.1f} MB). Maximum size is {cls.MAX_FILE_SIZE_MB} MB."
        
        return True, ""
    
    @classmethod
    def validate_duration(cls, duration_seconds: float) -> tuple[bool, str]:
        """Validate audio duration is within acceptable range."""
        if duration_seconds < cls.MIN_DURATION_SECONDS:
            return False, f"Audio too short ({duration_seconds:.1f}s). Minimum duration is {cls.MIN_DURATION_SECONDS}s."
        
        if duration_seconds > cls.MAX_DURATION_SECONDS:
            return False, f"Audio too long ({duration_seconds:.1f}s). Maximum duration is {cls.MAX_DURATION_SECONDS}s."
        
        return True, ""
    
    @classmethod
    async def validate_audio_file(cls, file_path: str) -> tuple[bool, str, dict]:
        """
        Comprehensive audio file validation.
        Returns (is_valid, error_message, metadata).
        """
        from pathlib import Path
        import os
        
        path = Path(file_path)
        metadata = {
            "filename": path.name,
            "extension": path.suffix.lower(),
            "file_size_bytes": 0,
            "duration_seconds": None,
        }
        
        # Check file exists
        if not path.exists():
            return False, f"File not found: {file_path}", metadata
        
        # Check extension
        if not cls.validate_file_extension(path.name):
            return False, f"Unsupported audio format: {path.suffix}. Supported: {', '.join(cls.SUPPORTED_FORMATS)}", metadata
        
        # Check file size
        file_size = os.path.getsize(file_path)
        metadata["file_size_bytes"] = file_size
        is_valid, error = cls.validate_file_size(file_size)
        if not is_valid:
            return False, error, metadata
        
        # Try to get duration using mutagen
        try:
            from mutagen import File as MutagenFile
            audio = MutagenFile(file_path)
            if audio and audio.info:
                duration = audio.info.length
                metadata["duration_seconds"] = duration
                is_valid, error = cls.validate_duration(duration)
                if not is_valid:
                    return False, error, metadata
        except Exception as e:
            logger.warning(f"Could not read audio metadata for {file_path}: {e}")
            # Don't fail validation if we can't read metadata
        
        return True, "", metadata


class TranscriptValidator:
    """Validate transcription results."""
    
    MIN_TRANSCRIPT_LENGTH = 10
    
    @classmethod
    def validate_transcript(cls, transcript: str) -> tuple[bool, str, dict]:
        """
        Validate transcript content.
        Returns (is_valid, warning_message, metadata).
        """
        metadata = {
            "length": len(transcript) if transcript else 0,
            "word_count": len(transcript.split()) if transcript else 0,
            "is_empty": not transcript or not transcript.strip(),
            "is_short": False,
        }
        
        if metadata["is_empty"]:
            return False, "Transcript is empty. The audio may be silent or corrupted.", metadata
        
        if metadata["length"] < cls.MIN_TRANSCRIPT_LENGTH:
            metadata["is_short"] = True
            return True, "Transcript is very short. Audio may have limited speech content.", metadata
        
        return True, "", metadata


class AnalysisValidator:
    """Validate analysis results and provide confidence indicators."""
    
    LOW_CONFIDENCE_THRESHOLD = 50
    
    @classmethod
    def validate_analysis(cls, analysis: dict) -> tuple[bool, list[str], dict]:
        """
        Validate analysis results and identify low-confidence areas.
        Returns (is_valid, warnings, enhanced_analysis).
        """
        warnings = []
        enhanced = analysis.copy()
        
        # Check for missing required fields
        required_fields = ["performance_score", "call_reason", "call_outcome"]
        for field in required_fields:
            if field not in analysis or analysis[field] is None:
                warnings.append(f"Missing analysis field: {field}")
        
        # Check confidence scores
        confidence_fields = [
            ("call_reason_confidence", "call_reason"),
            ("call_outcome_confidence", "call_outcome"),
        ]
        
        for conf_field, related_field in confidence_fields:
            conf_value = analysis.get(conf_field, 0)
            if conf_value and conf_value < cls.LOW_CONFIDENCE_THRESHOLD:
                warnings.append(
                    f"Low confidence ({conf_value}%) for {related_field}. "
                    "Result may be uncertain."
                )
                enhanced[f"{related_field}_uncertain"] = True
        
        # Add overall confidence indicator
        all_confidences = [
            analysis.get("call_reason_confidence", 50),
            analysis.get("call_outcome_confidence", 50),
        ]
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
        enhanced["overall_confidence"] = avg_confidence
        enhanced["analysis_warnings"] = warnings
        
        is_valid = len([w for w in warnings if "Missing" in w]) == 0
        return is_valid, warnings, enhanced


def log_request(func_name: str, request_data: dict, sanitize_keys: list[str] = None):
    """Log API request with optional key sanitization."""
    if sanitize_keys is None:
        sanitize_keys = ["api_key", "authorization", "password", "token"]
    
    sanitized = request_data.copy()
    for key in sanitize_keys:
        if key.lower() in {k.lower() for k in sanitized.keys()}:
            for k in list(sanitized.keys()):
                if k.lower() == key.lower():
                    sanitized[k] = "***REDACTED***"
    
    logger.info(f"[{func_name}] Request: {sanitized}")


def log_response(func_name: str, response_data: dict, duration_ms: float = None):
    """Log API response."""
    duration_str = f" ({duration_ms:.0f}ms)" if duration_ms else ""
    
    # Truncate large responses for logging
    log_data = str(response_data)
    if len(log_data) > 500:
        log_data = log_data[:500] + "..."
    
    logger.info(f"[{func_name}] Response{duration_str}: {log_data}")
