"""
TTS Provider Abstract Interface
다양한 TTS 엔진을 위한 추상 인터페이스
"""

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterable
from typing import Optional, Tuple

from ..core.exceptions import TTSError
from ..core.models import AudioFrame, TTSGenerationData, TTSRequest, TTSResponse


class TTSProvider(ABC):
    """TTS 제공자 추상 기본 클래스"""

    def __init__(self, name: str):
        self.name = name
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> bool:
        """TTS 엔진 초기화"""
        pass

    @abstractmethod
    async def generate_speech(self, request: TTSRequest) -> TTSResponse:
        """
        텍스트를 음성으로 변환

        Args:
            request: TTS 요청 데이터

        Returns:
            TTS 응답 데이터

        Raises:
            TTSError: TTS 생성 실패 시
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """TTS 엔진 사용 가능 여부 확인"""
        pass

    async def cleanup(self):
        """리소스 정리 (필요시 오버라이드)"""
        pass

    @property
    def is_initialized(self) -> bool:
        """초기화 상태 확인"""
        return self._initialized


class StreamingTTSProvider(TTSProvider):
    """스트리밍 TTS를 지원하는 추상 클래스"""

    @abstractmethod
    async def perform_tts_inference(
        self, text_input: AsyncIterable[str]
    ) -> Tuple[asyncio.Task, TTSGenerationData]:
        """
        스트리밍 TTS 추론 실행

        Args:
            text_input: 텍스트 스트림

        Returns:
            (실행 태스크, TTS 생성 데이터) 튜플
        """
        pass

    async def generate_audio_frames(
        self, text: str, chunk_size: int = 8192
    ) -> AsyncIterable[AudioFrame]:
        """
        텍스트를 오디오 프레임 스트림으로 변환

        Args:
            text: 변환할 텍스트
            chunk_size: 오디오 청크 크기

        Yields:
            AudioFrame: 오디오 프레임들
        """
        # 기본 구현: 전체 오디오를 생성 후 청크로 분할
        request = TTSRequest(text=text)
        response = await self.generate_speech(request)

        if not response.is_valid():
            raise TTSError(f"TTS 생성 실패: {response.error_message}", self.name)

        # 오디오 데이터를 청크로 분할
        audio_data = response.audio_data
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i : i + chunk_size]

            frame = AudioFrame(
                data=chunk,
                timestamp=time.time(),
                duration=0.1,  # 기본값, 구현체에서 조정 가능
                is_real_audio=True,
            )

            yield frame


class TTSProviderManager:
    """TTS 제공자 관리 클래스"""

    def __init__(self):
        self._providers = {}
        self._default_provider = None

    def register_provider(self, name: str, provider: TTSProvider):
        """TTS 제공자 등록"""
        self._providers[name] = provider

        # 첫 번째 등록된 제공자를 기본값으로 설정
        if self._default_provider is None:
            self._default_provider = name

    def get_provider(self, name: Optional[str] = None) -> TTSProvider:
        """TTS 제공자 반환"""
        provider_name = name or self._default_provider

        if provider_name not in self._providers:
            raise TTSError(f"TTS 제공자 '{provider_name}'를 찾을 수 없습니다")

        return self._providers[provider_name]

    def list_providers(self) -> list[str]:
        """등록된 제공자 목록 반환"""
        return list(self._providers.keys())

    def get_available_providers(self) -> list[str]:
        """사용 가능한 제공자 목록 반환"""
        return [
            name
            for name, provider in self._providers.items()
            if provider.is_available()
        ]

    async def initialize_all(self) -> dict[str, bool]:
        """모든 제공자 초기화"""
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.initialize()
            except Exception:
                results[name] = False
        return results

    async def cleanup_all(self):
        """모든 제공자 정리"""
        for provider in self._providers.values():
            await provider.cleanup()
