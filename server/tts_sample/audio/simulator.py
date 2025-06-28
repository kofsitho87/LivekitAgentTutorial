"""
Simulation Audio Player Implementation
테스트 및 폴백용 시뮬레이션 오디오 재생 구현체
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterable

from ..config.settings import get_pipeline_config
from ..core.models import AudioFrame, AudioOutputData
from .base import StreamingAudioPlayer

logger = logging.getLogger(__name__)


class SimulatorAudioPlayer(StreamingAudioPlayer):
    """시뮬레이션 오디오 재생자 (테스트 및 폴백용)"""

    def __init__(self):
        super().__init__("Simulator")
        self.play_counter = 0

    async def initialize(self) -> bool:
        """시뮬레이션 오디오 시스템 초기화 (항상 성공)"""
        self._initialized = True
        logger.info("✅ 시뮬레이션 오디오 시스템 초기화 완료")
        return True

    def is_available(self) -> bool:
        """시뮬레이션 오디오는 항상 사용 가능"""
        return True

    async def play_audio_data(self, audio_data: bytes) -> bool:
        """시뮬레이션 오디오 재생"""
        self.play_counter += 1

        try:
            # 실제 재생 시간 시뮬레이션
            play_time = len(audio_data) / 8000.0  # 가정: 8KB/초
            play_time = min(play_time, 5.0)  # 최대 5초

            logger.info(
                f"🎭 시뮬레이션 재생 #{self.play_counter}: {len(audio_data)} 바이트 ({play_time:.2f}초)"
            )

            await asyncio.sleep(play_time)

            logger.info(f"✅ 시뮬레이션 재생 #{self.play_counter} 완료")
            return True

        except Exception as e:
            logger.error(f"❌ 시뮬레이션 재생 오류: {e}")
            return False

    async def perform_audio_forwarding(
        self, audio_input: AsyncIterable[AudioFrame]
    ) -> AsyncIterable[AudioOutputData]:
        """스트리밍 시뮬레이션 오디오 재생"""
        logger.info("🔊 시뮬레이션 오디오 포워딩 시작")
        frame_count = 0
        pipeline_config = get_pipeline_config()

        try:
            self._is_playing = True

            async for frame in audio_input:
                frame_count += 1
                start_time = time.time()

                try:
                    logger.info(
                        f"🎭 시뮬레이션 프레임 #{frame_count} 처리 중... ({len(frame.data)} 바이트)"
                    )

                    # 시뮬레이션 재생
                    success = await self.play_audio_data(frame.data)
                    play_time = time.time() - start_time

                    # 결과 데이터 생성
                    output_data = AudioOutputData(
                        frame=frame,
                        success=success,
                        duration=play_time,
                        player_name=self.name,
                    )

                    yield output_data

                    # 프레임 간 지연
                    await asyncio.sleep(pipeline_config.simulation_frame_delay)

                except Exception as e:
                    play_time = time.time() - start_time
                    error_msg = f"시뮬레이션 재생 오류: {e}"
                    logger.error(f"❌ {error_msg}")

                    output_data = AudioOutputData(
                        frame=frame,
                        success=False,
                        duration=play_time,
                        player_name=self.name,
                        error_message=error_msg,
                    )

                    yield output_data

            logger.info(f"🎉 시뮬레이션 오디오 포워딩 완료 - 총 {frame_count} 프레임")

        except Exception as e:
            logger.error(f"❌ 시뮬레이션 오디오 포워딩 오류: {e}")
        finally:
            self._is_playing = False
            logger.info("📡 시뮬레이션 오디오 포워딩 종료")

    async def cleanup(self):
        """리소스 정리"""
        self.play_counter = 0
        self._initialized = False
        logger.info("🧹 시뮬레이션 오디오 리소스 정리 완료")


class LogAudioPlayer(StreamingAudioPlayer):
    """로그 전용 오디오 재생자 (실제 재생 없이 로그만 출력)"""

    def __init__(self):
        super().__init__("Logger")

    async def initialize(self) -> bool:
        """로그 오디오 시스템 초기화"""
        self._initialized = True
        logger.info("✅ 로그 오디오 시스템 초기화 완료")
        return True

    def is_available(self) -> bool:
        """로그 오디오는 항상 사용 가능"""
        return True

    async def play_audio_data(self, audio_data: bytes) -> bool:
        """로그 출력 (실제 재생 없음)"""
        try:
            logger.info(f"📝 로그 재생: {len(audio_data)} 바이트")

            # 데이터 내용 일부 표시 (텍스트인 경우)
            try:
                text_preview = audio_data[:50].decode("utf-8", errors="ignore")
                if text_preview.strip():
                    logger.info(f"📄 내용 미리보기: '{text_preview}'")
            except:
                pass

            return True

        except Exception as e:
            logger.error(f"❌ 로그 재생 오류: {e}")
            return False

    async def perform_audio_forwarding(
        self, audio_input: AsyncIterable[AudioFrame]
    ) -> AsyncIterable[AudioOutputData]:
        """로그 전용 오디오 포워딩"""
        logger.info("🔊 로그 오디오 포워딩 시작")
        frame_count = 0

        try:
            self._is_playing = True

            async for frame in audio_input:
                frame_count += 1
                start_time = time.time()

                logger.info(f"📝 로그 프레임 #{frame_count}: {len(frame.data)} 바이트")

                # 로그 "재생"
                success = await self.play_audio_data(frame.data)
                play_time = time.time() - start_time

                output_data = AudioOutputData(
                    frame=frame,
                    success=success,
                    duration=play_time,
                    player_name=self.name,
                )

                yield output_data

            logger.info(f"🎉 로그 오디오 포워딩 완료 - 총 {frame_count} 프레임")

        except Exception as e:
            logger.error(f"❌ 로그 오디오 포워딩 오류: {e}")
        finally:
            self._is_playing = False
            logger.info("📡 로그 오디오 포워딩 종료")

    async def cleanup(self):
        """리소스 정리"""
        self._initialized = False
        logger.info("🧹 로그 오디오 리소스 정리 완료")


class NullAudioPlayer(StreamingAudioPlayer):
    """Null 오디오 재생자 (아무것도 하지 않음)"""

    def __init__(self):
        super().__init__("Null")

    async def initialize(self) -> bool:
        """Null 오디오 시스템 초기화"""
        self._initialized = True
        return True

    def is_available(self) -> bool:
        """Null 오디오는 항상 사용 가능"""
        return True

    async def play_audio_data(self, audio_data: bytes) -> bool:
        """아무것도 하지 않음"""
        return True

    async def perform_audio_forwarding(
        self, audio_input: AsyncIterable[AudioFrame]
    ) -> AsyncIterable[AudioOutputData]:
        """Null 오디오 포워딩 (빠른 처리)"""
        frame_count = 0

        try:
            self._is_playing = True

            async for frame in audio_input:
                frame_count += 1

                output_data = AudioOutputData(
                    frame=frame, success=True, duration=0.0, player_name=self.name
                )

                yield output_data

        finally:
            self._is_playing = False


# 편의 함수들
def create_simulator_player() -> SimulatorAudioPlayer:
    """시뮬레이션 오디오 재생자 생성"""
    return SimulatorAudioPlayer()


def create_log_player() -> LogAudioPlayer:
    """로그 오디오 재생자 생성"""
    return LogAudioPlayer()


def create_null_player() -> NullAudioPlayer:
    """Null 오디오 재생자 생성"""
    return NullAudioPlayer()


async def quick_simulate_play(audio_data: bytes) -> bool:
    """시뮬레이션으로 빠른 오디오 재생"""
    player = create_simulator_player()
    await player.initialize()

    try:
        success = await player.play_audio_data(audio_data)
        return success
    finally:
        await player.cleanup()
