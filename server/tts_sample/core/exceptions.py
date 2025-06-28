"""
Exception Classes for TTS Pipeline
TTS 파이프라인의 예외 처리 클래스들
"""


class TTSPipelineError(Exception):
    """TTS 파이프라인 기본 예외"""

    pass


class TTSError(TTSPipelineError):
    """TTS 관련 예외"""

    def __init__(
        self, message: str, provider: str = "unknown", original_error: Exception = None
    ):
        super().__init__(message)
        self.provider = provider
        self.original_error = original_error

    def __str__(self):
        base_msg = f"TTS Error ({self.provider}): {super().__str__()}"
        if self.original_error:
            base_msg += f" | Original: {self.original_error}"
        return base_msg


class AudioError(TTSPipelineError):
    """오디오 재생 관련 예외"""

    def __init__(
        self,
        message: str,
        audio_system: str = "unknown",
        original_error: Exception = None,
    ):
        super().__init__(message)
        self.audio_system = audio_system
        self.original_error = original_error

    def __str__(self):
        base_msg = f"Audio Error ({self.audio_system}): {super().__str__()}"
        if self.original_error:
            base_msg += f" | Original: {self.original_error}"
        return base_msg


class ChannelError(TTSPipelineError):
    """채널 관련 예외"""

    pass


class ConfigurationError(TTSPipelineError):
    """설정 관련 예외"""

    pass


class OpenAITTSError(TTSError):
    """OpenAI TTS 전용 예외"""

    def __init__(
        self, message: str, status_code: int = None, original_error: Exception = None
    ):
        super().__init__(message, "OpenAI", original_error)
        self.status_code = status_code


class PygameAudioError(AudioError):
    """Pygame 오디오 관련 예외"""

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, "pygame", original_error)


class StreamTeeError(ChannelError):
    """Stream Tee 관련 예외"""

    pass


class AudioPlayerError(AudioError):
    """오디오 재생자 관련 예외"""

    def __init__(
        self,
        message: str,
        player_name: str = "unknown",
        original_error: Exception = None,
    ):
        super().__init__(message, player_name, original_error)


class PipelineError(TTSPipelineError):
    """파이프라인 관련 예외"""

    def __init__(
        self,
        message: str,
        component: str = "pipeline",
        original_error: Exception = None,
    ):
        super().__init__(message)
        self.component = component
        self.original_error = original_error

    def __str__(self):
        base_msg = f"Pipeline Error ({self.component}): {super().__str__()}"
        if self.original_error:
            base_msg += f" | Original: {self.original_error}"
        return base_msg


class PipelineTimeoutError(TTSPipelineError):
    """파이프라인 타임아웃 예외"""

    def __init__(self, message: str, timeout_seconds: float):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds

    def __str__(self):
        return f"Pipeline Timeout ({self.timeout_seconds}s): {super().__str__()}"
