"""
Audio Player Abstract Interface
다양한 오디오 재생 엔진을 위한 추상 인터페이스
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterable
from typing import Any, Dict, Optional

from ..core.exceptions import AudioPlayerError
from ..core.models import AudioFrame, AudioOutputData

logger = logging.getLogger(__name__)


class AudioPlayer(ABC):
    """오디오 재생자 추상 기본 클래스"""

    def __init__(self, name: str):
        self.name = name
        self._initialized = False
        self._is_playing = False

    @abstractmethod
    async def initialize(self) -> bool:
        """오디오 시스템 초기화"""
        pass

    @abstractmethod
    async def play_audio_data(self, audio_data: bytes) -> bool:
        """
        오디오 데이터 재생

        Args:
            audio_data: 재생할 오디오 데이터 (MP3, WAV 등)

        Returns:
            재생 성공 여부
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """오디오 재생자 사용 가능 여부"""
        pass

    async def play_audio_frame(self, frame: AudioFrame) -> bool:
        """
        오디오 프레임 재생

        Args:
            frame: 재생할 오디오 프레임

        Returns:
            재생 성공 여부
        """
        return await self.play_audio_data(frame.data)

    async def stop(self):
        """재생 중지 (필요시 오버라이드)"""
        self._is_playing = False

    async def pause(self):
        """재생 일시정지 (필요시 오버라이드)"""
        pass

    async def resume(self):
        """재생 재개 (필요시 오버라이드)"""
        pass

    async def cleanup(self):
        """리소스 정리 (필요시 오버라이드)"""
        self._initialized = False
        self._is_playing = False

    @property
    def is_initialized(self) -> bool:
        """초기화 상태 확인"""
        return self._initialized

    @property
    def is_playing(self) -> bool:
        """재생 상태 확인"""
        return self._is_playing


class StreamingAudioPlayer(AudioPlayer):
    """스트리밍 오디오 재생을 지원하는 추상 클래스"""

    @abstractmethod
    async def perform_audio_forwarding(
        self, audio_input: AsyncIterable[AudioFrame]
    ) -> AsyncIterable[AudioOutputData]:
        """
        스트리밍 오디오 재생 실행

        Args:
            audio_input: 오디오 프레임 스트림

        Yields:
            AudioOutputData: 재생 결과 데이터
        """
        pass

    async def stream_audio_frames(
        self, frames: AsyncIterable[AudioFrame]
    ) -> Dict[str, Any]:
        """
        오디오 프레임 스트림을 재생하고 통계 반환

        Args:
            frames: 오디오 프레임 스트림

        Returns:
            재생 통계 딕셔너리
        """
        stats = {
            "total_frames": 0,
            "successful_frames": 0,
            "failed_frames": 0,
            "total_duration": 0.0,
            "errors": [],
        }

        try:
            self._is_playing = True

            async for output_data in self.perform_audio_forwarding(frames):
                stats["total_frames"] += 1

                if output_data.success:
                    stats["successful_frames"] += 1
                    stats["total_duration"] += output_data.duration
                else:
                    stats["failed_frames"] += 1
                    if output_data.error_message:
                        stats["errors"].append(output_data.error_message)

        except Exception as e:
            logger.error(f"❌ 스트림 재생 오류: {e}")
            stats["errors"].append(str(e))
        finally:
            self._is_playing = False

        return stats


class AudioPlayerManager:
    """오디오 재생자 관리 클래스"""

    def __init__(self):
        self._players = {}
        self._default_player = None

    def register_player(self, name: str, player: AudioPlayer):
        """오디오 재생자 등록"""
        self._players[name] = player

        # 첫 번째 등록된 재생자를 기본값으로 설정
        if self._default_player is None:
            self._default_player = name

    def get_player(self, name: Optional[str] = None) -> AudioPlayer:
        """오디오 재생자 반환"""
        player_name = name or self._default_player

        if player_name not in self._players:
            raise AudioPlayerError(f"오디오 재생자 '{player_name}'를 찾을 수 없습니다")

        return self._players[player_name]

    def list_players(self) -> list[str]:
        """등록된 재생자 목록 반환"""
        return list(self._players.keys())

    def get_available_players(self) -> list[str]:
        """사용 가능한 재생자 목록 반환"""
        return [name for name, player in self._players.items() if player.is_available()]

    async def initialize_all(self) -> Dict[str, bool]:
        """모든 재생자 초기화"""
        results = {}
        for name, player in self._players.items():
            try:
                results[name] = await player.initialize()
            except Exception as e:
                logger.error(f"❌ 오디오 재생자 '{name}' 초기화 실패: {e}")
                results[name] = False
        return results

    async def cleanup_all(self):
        """모든 재생자 정리"""
        for player in self._players.values():
            try:
                await player.cleanup()
            except Exception as e:
                logger.error(f"❌ 오디오 재생자 정리 실패: {e}")


# LiveKit 스타일 인터페이스 호환성을 위한 헬퍼 함수들
async def perform_audio_forwarding_with_player(
    player: StreamingAudioPlayer, audio_input: AsyncIterable[AudioFrame]
) -> AsyncIterable[AudioOutputData]:
    """
    LiveKit 스타일 오디오 포워딩 인터페이스

    Args:
        player: 스트리밍 오디오 재생자
        audio_input: 오디오 프레임 스트림

    Yields:
        AudioOutputData: 재생 결과
    """
    async for output_data in player.perform_audio_forwarding(audio_input):
        yield output_data
