"""
OpenAI TTS Implementation
OpenAI의 Text-to-Speech API를 사용하는 TTS 구현체
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterable
from typing import Optional, Tuple

from ..config.settings import get_channel_config, get_openai_config
from ..core.channels import Chan
from ..core.exceptions import OpenAITTSError
from ..core.models import AudioFrame, TTSGenerationData, TTSRequest, TTSResponse
from .base import StreamingTTSProvider

logger = logging.getLogger(__name__)

# OpenAI 라이브러리 import 처리
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False


class OpenAITTSProvider(StreamingTTSProvider):
    """OpenAI TTS API를 사용하는 TTS 제공자"""

    def __init__(self, config: Optional[object] = None):
        super().__init__("OpenAI")
        self.config = config or get_openai_config()
        self.client: Optional[OpenAI] = None

    async def initialize(self) -> bool:
        """OpenAI 클라이언트 초기화"""
        try:
            if not OPENAI_AVAILABLE:
                logger.warning("OpenAI 라이브러리가 설치되지 않았습니다")
                return False

            if not self.config.api_key:
                logger.warning("OpenAI API 키가 설정되지 않았습니다")
                return False

            self.client = OpenAI(api_key=self.config.api_key)
            self._initialized = True
            logger.info("✅ OpenAI TTS 클라이언트 초기화 완료")
            return True

        except Exception as e:
            logger.error(f"❌ OpenAI TTS 초기화 실패: {e}")
            return False

    def is_available(self) -> bool:
        """OpenAI TTS 사용 가능 여부 확인"""
        return OPENAI_AVAILABLE and self.config.api_key is not None

    async def generate_speech(self, request: TTSRequest) -> TTSResponse:
        """OpenAI TTS API를 사용하여 음성 생성"""
        if not self.client:
            raise OpenAITTSError("OpenAI 클라이언트가 초기화되지 않았습니다")

        start_time = time.time()

        try:
            logger.info(f"🎵 OpenAI TTS 생성 중: '{request.text[:30]}...'")

            # 비동기 처리를 위해 스레드풀 사용
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.audio.speech.create(
                    model=request.model,
                    voice=request.voice,
                    input=request.text,
                    response_format=request.response_format,
                ),
            )

            # 오디오 데이터 추출
            audio_data = response.content
            generation_time = time.time() - start_time

            logger.info(
                f"✅ OpenAI TTS 완료: {len(audio_data)} 바이트, {generation_time:.2f}초"
            )

            return TTSResponse(
                audio_data=audio_data,
                request=request,
                generation_time=generation_time,
                success=True,
            )

        except Exception as e:
            generation_time = time.time() - start_time
            error_msg = f"OpenAI TTS API 호출 실패: {e}"
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
        """스트리밍 TTS 추론 실행 (LiveKit 스타일)"""
        audio_ch = Chan()
        data = TTSGenerationData(audio_ch=audio_ch)

        async def _tts_inference_task() -> bool:
            logger.info("🔊 OpenAI TTS 추론 시작")
            frame_count = 0
            channel_config = get_channel_config()

            try:
                async for text in text_input:
                    logger.info(f"🎵 TTS 처리 중: '{text}'")

                    try:
                        # OpenAI TTS로 음성 생성
                        request = TTSRequest(
                            text=text,
                            model=self.config.model,
                            voice=self.config.voice,
                            response_format=self.config.response_format,
                        )

                        response = await self.generate_speech(request)

                        if not response.is_valid():
                            raise OpenAITTSError(response.error_message)

                        # 오디오를 청크로 분할하여 스트리밍
                        audio_data = response.audio_data
                        chunk_size = channel_config.chunk_size
                        total_chunks = len(audio_data) // chunk_size + (
                            1 if len(audio_data) % chunk_size else 0
                        )

                        logger.info(
                            f"📦 오디오 청크 분할: {len(audio_data)} 바이트 -> {total_chunks} 청크"
                        )

                        for i in range(0, len(audio_data), chunk_size):
                            frame_count += 1
                            chunk = audio_data[i : i + chunk_size]

                            audio_frame = AudioFrame(
                                data=chunk,
                                timestamp=time.time(),
                                duration=0.1,
                                is_real_audio=True,
                            )

                            audio_ch.send_nowait(audio_frame)
                            await asyncio.sleep(channel_config.stream_delay)

                        logger.info(
                            f"✅ OpenAI TTS 완료: '{text}' -> {total_chunks} 청크"
                        )

                    except Exception as e:
                        logger.error(f"❌ OpenAI TTS 실패: {e}")
                        # 실패 시 빈 응답으로 처리하고 계속 진행
                        continue

                logger.info(f"🎉 전체 OpenAI TTS 추론 완료 - 총 {frame_count} 프레임")
                return True

            except Exception as e:
                logger.error(f"❌ TTS 추론 오류: {e}")
                return False
            finally:
                # 채널 완료 표시
                audio_ch.mark_finished()
                logger.info("📡 OpenAI TTS 채널 완료 신호 전송")

        task = asyncio.create_task(_tts_inference_task())
        return task, data

    async def cleanup(self):
        """리소스 정리"""
        self.client = None
        self._initialized = False
        logger.info("🧹 OpenAI TTS 리소스 정리 완료")


# 편의 함수들
def create_openai_tts(api_key: Optional[str] = None) -> OpenAITTSProvider:
    """OpenAI TTS 제공자 생성 편의 함수"""
    config = get_openai_config()
    if api_key:
        config.api_key = api_key

    return OpenAITTSProvider(config)


async def quick_tts(text: str, voice: str = "nova") -> bytes:
    """빠른 TTS 생성 편의 함수"""
    provider = create_openai_tts()

    if not await provider.initialize():
        raise OpenAITTSError("OpenAI TTS 초기화 실패")

    request = TTSRequest(text=text, voice=voice)
    response = await provider.generate_speech(request)

    if not response.is_valid():
        raise OpenAITTSError(response.error_message)

    await provider.cleanup()
    return response.audio_data
