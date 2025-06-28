"""
Core Data Models
TTS 파이프라인에서 사용되는 핵심 데이터 구조들
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

from ..config.settings import get_audio_config

if TYPE_CHECKING:
    from .channels import Chan


@dataclass
class AudioFrame:
    """오디오 프레임 데이터 구조 (LiveKit rtc.AudioFrame 스타일)"""

    data: bytes
    sample_rate: int = field(default_factory=lambda: get_audio_config().sample_rate)
    duration: float = 0.1
    timestamp: float = field(default_factory=time.time)
    is_real_audio: bool = False  # 실제 오디오 데이터 여부

    def __post_init__(self):
        """생성 후 타임스탬프 설정"""
        if self.timestamp == 0:
            self.timestamp = time.time()

    @property
    def size_bytes(self) -> int:
        """오디오 데이터 크기 반환"""
        return len(self.data)

    def is_empty(self) -> bool:
        """빈 프레임인지 확인"""
        return len(self.data) == 0


@dataclass
class TTSGenerationData:
    """TTS 생성 데이터 구조 (LiveKit _TTSGenerationData 스타일)"""

    audio_ch: "Chan"

    def close(self):
        """TTS 생성 완료 시 채널 닫기"""
        self.audio_ch.close()


@dataclass
class AudioOutputData:
    """오디오 출력 데이터 구조 (LiveKit _AudioOutput 스타일)"""

    audio_frames: List[AudioFrame] = field(default_factory=list)
    first_frame_fut: asyncio.Future = field(default_factory=asyncio.Future)

    def __init__(
        self,
        audio_frames: List[AudioFrame] = None,
        first_frame_fut: asyncio.Future = None,
    ):
        """AudioOutputData 초기화"""
        self.audio_frames = audio_frames if audio_frames is not None else []
        self.first_frame_fut = (
            first_frame_fut if first_frame_fut is not None else asyncio.Future()
        )

    @property
    def total_frames(self) -> int:
        """총 프레임 수"""
        return len(self.audio_frames)

    @property
    def total_duration(self) -> float:
        """총 재생 시간"""
        return sum(frame.duration for frame in self.audio_frames)

    @property
    def total_size_bytes(self) -> int:
        """총 오디오 데이터 크기"""
        return sum(frame.size_bytes for frame in self.audio_frames)

    def get_real_audio_frames(self) -> List[AudioFrame]:
        """실제 오디오 프레임들만 반환"""
        return [frame for frame in self.audio_frames if frame.is_real_audio]

    def get_simulation_frames(self) -> List[AudioFrame]:
        """시뮬레이션 프레임들만 반환"""
        return [frame for frame in self.audio_frames if not frame.is_real_audio]


@dataclass
class TTSRequest:
    """TTS 요청 데이터"""

    text: str
    voice: str = "nova"
    model: str = "tts-1"
    response_format: str = "mp3"

    def __post_init__(self):
        """요청 유효성 검사"""
        if not self.text.strip():
            raise ValueError("TTS 텍스트가 비어있습니다")


@dataclass
class TTSResponse:
    """TTS 응답 데이터"""

    audio_data: bytes
    request: TTSRequest
    generation_time: float = 0.0
    success: bool = True
    error_message: str = ""

    @property
    def size_bytes(self) -> int:
        """오디오 데이터 크기"""
        return len(self.audio_data)

    def is_valid(self) -> bool:
        """유효한 응답인지 확인"""
        return self.success and len(self.audio_data) > 0
