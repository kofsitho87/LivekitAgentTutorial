"""
Simulation TTS Implementation
테스트 및 폴백용 시뮬레이션 TTS 구현체
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterable
from typing import Tuple

from ..config.settings import get_pipeline_config
from ..core.channels import Chan
from ..core.models import AudioFrame, TTSGenerationData, TTSRequest, TTSResponse
from .base import StreamingTTSProvider

logger = logging.getLogger(__name__)


class SimulatorTTSProvider(StreamingTTSProvider):
    """시뮬레이션 TTS 제공자 (테스트 및 폴백용)"""

    def __init__(self):
        super().__init__("Simulator")
        self.frame_counter = 0

    async def initialize(self) -> bool:
        """시뮬레이션 TTS 초기화 (항상 성공)"""
        self._initialized = True
        logger.info("✅ 시뮬레이션 TTS 초기화 완료")
        return True

    def is_available(self) -> bool:
        """시뮬레이션 TTS는 항상 사용 가능"""
        return True

    async def generate_speech(self, request: TTSRequest) -> TTSResponse:
        """시뮬레이션 음성 생성"""
        start_time = time.time()

        try:
            logger.info(f"🎭 시뮬레이션 TTS 생성 중: '{request.text[:30]}...'")

            # 실제 TTS 생성 시간 시뮬레이션
            words = request.text.split()
            simulation_time = len(words) * 0.1  # 단어당 0.1초
            await asyncio.sleep(simulation_time)

            # 가짜 오디오 데이터 생성
            fake_audio_data = f"SIMULATION_AUDIO:{request.text}".encode("utf-8")
            # 실제 음성 파일과 비슷한 크기로 패딩
            fake_audio_data += b"\x00" * (len(request.text) * 100)

            generation_time = time.time() - start_time

            logger.info(
                f"✅ 시뮬레이션 TTS 완료: {len(fake_audio_data)} 바이트, {generation_time:.2f}초"
            )

            return TTSResponse(
                audio_data=fake_audio_data,
                request=request,
                generation_time=generation_time,
                success=True,
            )

        except Exception as e:
            generation_time = time.time() - start_time
            error_msg = f"시뮬레이션 TTS 오류: {e}"
            logger.error(f"❌ {error_msg}")

            return TTSResponse(
                audio_data=b"",
                request=request,
                generation_time=generation_time,
                success=False,
                error_message=error_msg,
            )

    async def perform_tts_inference(
        self, text_input: AsyncIterable[str]
    ) -> Tuple[asyncio.Task, TTSGenerationData]:
        """스트리밍 시뮬레이션 TTS 추론"""
        audio_ch = Chan()
        data = TTSGenerationData(audio_ch=audio_ch)

        async def _tts_inference_task() -> bool:
            logger.info("🔊 시뮬레이션 TTS 추론 시작")
            frame_count = 0
            pipeline_config = get_pipeline_config()

            try:
                async for text in text_input:
                    logger.info(f"🎭 시뮬레이션 TTS 처리 중: '{text}'")

                    # 텍스트를 분석하여 프레임 수 결정
                    frames_per_text = len(text.split()) * 2  # 단어당 2개 프레임

                    for i in range(frames_per_text):
                        frame_count += 1
                        self.frame_counter += 1

                        # 시뮬레이션 오디오 데이터 생성
                        fake_audio_data = (
                            f"sim_frame_{self.frame_counter}_{text[:10]}".encode(
                                "utf-8"
                            )
                        )

                        audio_frame = AudioFrame(
                            data=fake_audio_data,
                            timestamp=time.time(),
                            duration=0.1,
                            is_real_audio=False,  # 시뮬레이션 표시
                        )

                        audio_ch.send_nowait(audio_frame)
                        await asyncio.sleep(pipeline_config.simulation_frame_delay)

                    logger.info(
                        f"✅ 시뮬레이션 TTS 완료: '{text}' -> {frames_per_text} 프레임"
                    )

                logger.info(
                    f"🎉 전체 시뮬레이션 TTS 추론 완료 - 총 {frame_count} 프레임"
                )
                return True

            except Exception as e:
                logger.error(f"❌ 시뮬레이션 TTS 추론 오류: {e}")
                return False
            finally:
                # 채널 완료 표시
                audio_ch.mark_finished()
                logger.info("📡 시뮬레이션 TTS 채널 완료 신호 전송")

        task = asyncio.create_task(_tts_inference_task())
        return task, data

    async def cleanup(self):
        """리소스 정리"""
        self.frame_counter = 0
        self._initialized = False
        logger.info("🧹 시뮬레이션 TTS 리소스 정리 완료")


class EchoTTSProvider(StreamingTTSProvider):
    """에코 TTS 제공자 (입력 텍스트를 그대로 오디오로 변환하는 시뮬레이션)"""

    def __init__(self):
        super().__init__("Echo")

    async def initialize(self) -> bool:
        """에코 TTS 초기화"""
        self._initialized = True
        logger.info("✅ 에코 TTS 초기화 완료")
        return True

    def is_available(self) -> bool:
        """에코 TTS는 항상 사용 가능"""
        return True

    async def generate_speech(self, request: TTSRequest) -> TTSResponse:
        """텍스트를 그대로 오디오로 변환 (에코)"""
        start_time = time.time()

        try:
            logger.info(f"🔊 에코 TTS: '{request.text}'")

            # 텍스트를 바이트로 변환 (UTF-8)
            audio_data = request.text.encode("utf-8")
            generation_time = time.time() - start_time

            return TTSResponse(
                audio_data=audio_data,
                request=request,
                generation_time=generation_time,
                success=True,
            )

        except Exception as e:
            generation_time = time.time() - start_time
            error_msg = f"에코 TTS 오류: {e}"

            return TTSResponse(
                audio_data=b"",
                request=request,
                generation_time=generation_time,
                success=False,
                error_message=error_msg,
            )

    async def perform_tts_inference(
        self, text_input: AsyncIterable[str]
    ) -> Tuple[asyncio.Task, TTSGenerationData]:
        """에코 TTS 스트리밍 추론"""
        audio_ch = Chan()
        data = TTSGenerationData(audio_ch=audio_ch)

        async def _tts_inference_task() -> bool:
            logger.info("🔊 에코 TTS 추론 시작")
            frame_count = 0

            try:
                async for text in text_input:
                    logger.info(f"🔊 에코 TTS: '{text}'")

                    # 텍스트를 직접 오디오 프레임으로 변환
                    frame_count += 1
                    audio_data = text.encode("utf-8")

                    audio_frame = AudioFrame(
                        data=audio_data,
                        timestamp=time.time(),
                        duration=len(text) * 0.05,  # 글자 수에 비례한 길이
                        is_real_audio=False,
                    )

                    audio_ch.send_nowait(audio_frame)
                    await asyncio.sleep(0.1)

                logger.info(f"🎉 에코 TTS 추론 완료 - 총 {frame_count} 프레임")
                return True

            except Exception as e:
                logger.error(f"❌ 에코 TTS 추론 오류: {e}")
                return False
            finally:
                audio_ch.mark_finished()
                logger.info("📡 에코 TTS 채널 완료 신호 전송")

        task = asyncio.create_task(_tts_inference_task())
        return task, data


# 편의 함수들
def create_simulator_tts() -> SimulatorTTSProvider:
    """시뮬레이션 TTS 제공자 생성"""
    return SimulatorTTSProvider()


def create_echo_tts() -> EchoTTSProvider:
    """에코 TTS 제공자 생성"""
    return EchoTTSProvider()


async def quick_simulation(text: str) -> bytes:
    """빠른 시뮬레이션 TTS"""
    provider = create_simulator_tts()
    await provider.initialize()

    request = TTSRequest(text=text)
    response = await provider.generate_speech(request)

    await provider.cleanup()
    return response.audio_data
