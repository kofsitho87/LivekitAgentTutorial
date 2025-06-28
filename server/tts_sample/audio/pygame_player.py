"""
Pygame Audio Player Implementation
pygame을 사용하는 오디오 재생 구현체
"""

import asyncio
import logging
import tempfile
import time
from collections.abc import AsyncIterable
from typing import Optional

from ..config.settings import get_audio_config
from ..core.exceptions import AudioPlayerError
from ..core.models import AudioFrame, AudioOutputData
from .base import StreamingAudioPlayer

logger = logging.getLogger(__name__)

# pygame 라이브러리 import 처리
try:
    import pygame
    import pygame.mixer

    PYGAME_AVAILABLE = True
except ImportError:
    pygame = None
    PYGAME_AVAILABLE = False


class PygameAudioPlayer(StreamingAudioPlayer):
    """pygame을 사용하는 오디오 재생자"""

    def __init__(self, config: Optional[object] = None):
        super().__init__("Pygame")
        self.config = config or get_audio_config()
        self._temp_files = []

    async def initialize(self) -> bool:
        """pygame mixer 초기화"""
        try:
            if not PYGAME_AVAILABLE:
                logger.warning("pygame 라이브러리가 설치되지 않았습니다")
                return False

            # pygame mixer 초기화
            pygame.mixer.pre_init(
                frequency=self.config.sample_rate,
                size=self.config.bit_depth,
                channels=self.config.channels,
                buffer=self.config.buffer_size,
            )
            pygame.mixer.init()

            self._initialized = True
            logger.info("✅ pygame 오디오 시스템 초기화 완료")
            return True

        except Exception as e:
            logger.error(f"❌ pygame 오디오 초기화 실패: {e}")
            return False

    def is_available(self) -> bool:
        """pygame 사용 가능 여부 확인"""
        return PYGAME_AVAILABLE

    async def play_audio_data(self, audio_data: bytes) -> bool:
        """pygame으로 오디오 데이터 재생"""
        if not self._initialized:
            raise AudioPlayerError("pygame 오디오 시스템이 초기화되지 않았습니다")

        try:
            # 임시 파일에 오디오 데이터 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
                self._temp_files.append(temp_file_path)

            # pygame으로 재생
            pygame.mixer.music.load(temp_file_path)
            pygame.mixer.music.play()

            # 재생 완료까지 대기
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)

            # 임시 파일 정리
            try:
                import os

                os.unlink(temp_file_path)
                self._temp_files.remove(temp_file_path)
            except:
                pass  # 정리 실패는 무시

            return True

        except Exception as e:
            logger.error(f"❌ pygame 오디오 재생 실패: {e}")
            return False

    async def perform_audio_forwarding(
        self, audio_input: AsyncIterable[AudioFrame]
    ) -> AsyncIterable[AudioOutputData]:
        """스트리밍 오디오 재생 실행"""
        logger.info("🔊 pygame 오디오 포워딩 시작")
        frame_count = 0

        try:
            self._is_playing = True

            async for frame in audio_input:
                frame_count += 1
                start_time = time.time()

                try:
                    logger.info(
                        f"🎵 pygame 프레임 #{frame_count} 재생 중... ({len(frame.data)} 바이트)"
                    )

                    # 오디오 프레임 재생
                    success = await self.play_audio_data(frame.data)
                    play_time = time.time() - start_time

                    if success:
                        logger.info(
                            f"✅ pygame 프레임 #{frame_count} 재생 완료 ({play_time:.2f}초)"
                        )
                    else:
                        logger.warning(f"⚠️ pygame 프레임 #{frame_count} 재생 실패")

                    # 결과 데이터 생성
                    output_data = AudioOutputData(
                        frame=frame,
                        success=success,
                        duration=play_time,
                        player_name=self.name,
                    )

                    yield output_data

                except Exception as e:
                    play_time = time.time() - start_time
                    error_msg = f"pygame 재생 오류: {e}"
                    logger.error(f"❌ {error_msg}")

                    output_data = AudioOutputData(
                        frame=frame,
                        success=False,
                        duration=play_time,
                        player_name=self.name,
                        error_message=error_msg,
                    )

                    yield output_data

            logger.info(f"🎉 pygame 오디오 포워딩 완료 - 총 {frame_count} 프레임")

        except Exception as e:
            logger.error(f"❌ pygame 오디오 포워딩 오류: {e}")
        finally:
            self._is_playing = False
            logger.info("📡 pygame 오디오 포워딩 종료")

    async def stop(self):
        """pygame 재생 중지"""
        try:
            if pygame and pygame.mixer.get_init():
                pygame.mixer.music.stop()
            self._is_playing = False
            logger.info("⏹️ pygame 재생 중지")
        except Exception as e:
            logger.error(f"❌ pygame 중지 오류: {e}")

    async def pause(self):
        """pygame 재생 일시정지"""
        try:
            if pygame and pygame.mixer.get_init():
                pygame.mixer.music.pause()
            logger.info("⏸️ pygame 재생 일시정지")
        except Exception as e:
            logger.error(f"❌ pygame 일시정지 오류: {e}")

    async def resume(self):
        """pygame 재생 재개"""
        try:
            if pygame and pygame.mixer.get_init():
                pygame.mixer.music.unpause()
            logger.info("▶️ pygame 재생 재개")
        except Exception as e:
            logger.error(f"❌ pygame 재개 오류: {e}")

    async def cleanup(self):
        """pygame 리소스 정리"""
        try:
            await self.stop()

            # 임시 파일들 정리
            import os

            for temp_file in self._temp_files[:]:
                try:
                    os.unlink(temp_file)
                    self._temp_files.remove(temp_file)
                except:
                    pass

            # pygame mixer 종료
            if pygame and pygame.mixer.get_init():
                pygame.mixer.quit()

            self._initialized = False
            logger.info("🧹 pygame 오디오 리소스 정리 완료")

        except Exception as e:
            logger.error(f"❌ pygame 정리 오류: {e}")


# 편의 함수들
def create_pygame_player() -> PygameAudioPlayer:
    """pygame 오디오 재생자 생성"""
    return PygameAudioPlayer()


async def quick_play_with_pygame(audio_data: bytes) -> bool:
    """pygame으로 빠른 오디오 재생"""
    player = create_pygame_player()

    if not await player.initialize():
        raise AudioPlayerError("pygame 오디오 초기화 실패")

    try:
        success = await player.play_audio_data(audio_data)
        return success
    finally:
        await player.cleanup()


# 호환성을 위한 별칭
def is_pygame_available() -> bool:
    """pygame 사용 가능 여부 확인"""
    return PYGAME_AVAILABLE
