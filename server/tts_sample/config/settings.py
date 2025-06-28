"""
TTS Pipeline Configuration Settings
모든 설정값을 중앙에서 관리하는 모듈
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class OpenAIConfig:
    """OpenAI TTS 관련 설정"""

    model: str = "tts-1"  # "tts-1" 또는 "tts-1-hd"
    voice: str = "nova"  # alloy, echo, fable, onyx, nova, shimmer
    response_format: str = "mp3"
    api_key: Optional[str] = None

    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("OPENAI_API_KEY")


@dataclass
class AudioConfig:
    """오디오 재생 관련 설정"""

    sample_rate: int = 22050
    buffer_size: int = 512
    channels: int = 2
    bit_depth: int = -16  # pygame mixer 설정용
    chunk_batch_size: int = 5  # 몇 개의 청크를 모아서 재생할지


@dataclass
class ChannelConfig:
    """채널 및 스트리밍 관련 설정"""

    timeout_seconds: float = 30.0  # OpenAI API 대기 시간
    chunk_size: int = 8192  # TTS 오디오 청크 크기 (8KB)
    stream_delay: float = 0.001  # 청크 간 스트리밍 지연
    tee_num_streams: int = 2  # Stream Tee 분할 수


@dataclass
class PipelineConfig:
    """파이프라인 전체 설정"""

    llm_stream_delay: float = 0.5  # LLM 스트리밍 시뮬레이션 지연
    simulation_frame_delay: float = 0.05  # 시뮬레이션 오디오 프레임 지연
    audio_frame_duration: float = 0.1  # 오디오 프레임 기본 길이


@dataclass
class LoggingConfig:
    """로깅 관련 설정"""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# 기본 설정 인스턴스들
DEFAULT_OPENAI_CONFIG = OpenAIConfig()
DEFAULT_AUDIO_CONFIG = AudioConfig()
DEFAULT_CHANNEL_CONFIG = ChannelConfig()
DEFAULT_PIPELINE_CONFIG = PipelineConfig()
DEFAULT_LOGGING_CONFIG = LoggingConfig()


# 샘플 텍스트 데이터
DEFAULT_TEXT_CHUNKS = [
    "Hello, how are you?",
    "I'm doing well, thank you!",
    "What's your name?",
    "My name is John.",
    "Nice to meet you, John.",
]


def get_openai_config() -> OpenAIConfig:
    """OpenAI 설정 반환"""
    return DEFAULT_OPENAI_CONFIG


def get_audio_config() -> AudioConfig:
    """오디오 설정 반환"""
    return DEFAULT_AUDIO_CONFIG


def get_channel_config() -> ChannelConfig:
    """채널 설정 반환"""
    return DEFAULT_CHANNEL_CONFIG


def get_pipeline_config() -> PipelineConfig:
    """파이프라인 설정 반환"""
    return DEFAULT_PIPELINE_CONFIG


def get_logging_config() -> LoggingConfig:
    """로깅 설정 반환"""
    return DEFAULT_LOGGING_CONFIG
