"""
Pipeline Processor
개별 파이프라인 컴포넌트들을 처리하고 조정하는 프로세서
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any, Dict, List, Optional, Tuple

from ..audio.base import StreamingAudioPlayer
from ..config.settings import get_channel_config, get_pipeline_config
from ..core.channels import StreamTee
from ..core.exceptions import AudioPlayerError, PipelineError, TTSError
from ..core.models import AudioFrame, AudioOutputData, TTSGenerationData
from ..tts.base import StreamingTTSProvider

logger = logging.getLogger(__name__)


class TextStreamProcessor:
    """텍스트 스트림 처리기"""

    def __init__(self):
        self.processed_chunks = 0

    async def create_text_stream(self, texts: List[str]) -> AsyncIterator[str]:
        """텍스트 목록을 비동기 스트림으로 변환"""
        pipeline_config = get_pipeline_config()

        logger.info(f"📝 텍스트 스트림 생성: {len(texts)}개 청크")

        for i, text in enumerate(texts, 1):
            self.processed_chunks += 1
            logger.info(
                f"📤 텍스트 청크 #{i}: '{text[:50]}{'...' if len(text) > 50 else ''}'"
            )

            yield text

            # 청크 간 지연
            if i < len(texts):
                await asyncio.sleep(pipeline_config.text_chunk_delay)

        logger.info(f"✅ 텍스트 스트림 완료: 총 {self.processed_chunks}개 청크 처리")


class TTSProcessor:
    """TTS 처리기"""

    def __init__(self, tts_provider: StreamingTTSProvider):
        self.tts_provider = tts_provider
        self.processed_texts = 0
        self.generated_frames = 0

    async def process_tts_inference(
        self, text_input: AsyncIterable[str]
    ) -> Tuple[asyncio.Task, TTSGenerationData]:
        """TTS 추론 처리"""
        logger.info(f"🔊 TTS 추론 시작 - 제공자: {self.tts_provider.name}")

        if not self.tts_provider.is_initialized:
            if not await self.tts_provider.initialize():
                raise TTSError(f"TTS 제공자 '{self.tts_provider.name}' 초기화 실패")

        # TTS 제공자의 추론 실행
        task, tts_data = await self.tts_provider.perform_tts_inference(text_input)

        # 통계 수집을 위한 래퍼 태스크
        wrapped_task = asyncio.create_task(self._track_tts_task(task))

        return wrapped_task, tts_data

    async def _track_tts_task(self, original_task: asyncio.Task) -> bool:
        """TTS 태스크 추적"""
        try:
            result = await original_task
            logger.info(f"✅ TTS 추론 완료 - 제공자: {self.tts_provider.name}")
            return result
        except Exception as e:
            logger.error(
                f"❌ TTS 추론 실패 - 제공자: {self.tts_provider.name}, 오류: {e}"
            )
            raise TTSError(f"TTS 추론 실패: {e}", self.tts_provider.name)


class AudioProcessor:
    """오디오 처리기"""

    def __init__(self, audio_player: StreamingAudioPlayer):
        self.audio_player = audio_player
        self.processed_frames = 0
        self.successful_frames = 0
        self.failed_frames = 0

    async def process_audio_forwarding(
        self, audio_input: AsyncIterable[AudioFrame]
    ) -> AsyncIterator[AudioOutputData]:
        """오디오 포워딩 처리"""
        logger.info(f"🔊 오디오 포워딩 시작 - 재생자: {self.audio_player.name}")

        if not self.audio_player.is_initialized:
            if not await self.audio_player.initialize():
                raise AudioPlayerError(
                    f"오디오 재생자 '{self.audio_player.name}' 초기화 실패"
                )

        # 오디오 재생자의 포워딩 실행
        async for output_data in self.audio_player.perform_audio_forwarding(
            audio_input
        ):
            self.processed_frames += 1

            if output_data.success:
                self.successful_frames += 1
            else:
                self.failed_frames += 1

            yield output_data

        logger.info(f"✅ 오디오 포워딩 완료 - 재생자: {self.audio_player.name}")
        logger.info(
            f"📊 통계 - 총: {self.processed_frames}, 성공: {self.successful_frames}, 실패: {self.failed_frames}"
        )


class StreamProcessor:
    """스트림 분배 처리기"""

    def __init__(self):
        self.tees_created = 0

    def create_stream_tee(self, input_stream: AsyncIterable[AudioFrame]) -> StreamTee:
        """스트림 분배기 생성"""
        self.tees_created += 1
        tee = StreamTee(input_stream)
        logger.info(f"🔀 스트림 분배기 #{self.tees_created} 생성")
        return tee


class PipelineComponentProcessor:
    """파이프라인 컴포넌트 통합 처리기"""

    def __init__(
        self, tts_provider: StreamingTTSProvider, audio_player: StreamingAudioPlayer
    ):
        self.text_processor = TextStreamProcessor()
        self.tts_processor = TTSProcessor(tts_provider)
        self.audio_processor = AudioProcessor(audio_player)
        self.stream_processor = StreamProcessor()

        self.start_time = None
        self.end_time = None

    async def process_full_pipeline(
        self, texts: List[str], timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """전체 파이프라인 처리"""
        self.start_time = time.time()
        pipeline_config = get_pipeline_config()
        channel_config = get_channel_config()

        # 기본 타임아웃 설정
        if timeout is None:
            timeout = pipeline_config.default_timeout

        logger.info(f"🚀 전체 파이프라인 시작 - 타임아웃: {timeout}초")

        try:
            # 1. 텍스트 스트림 생성
            text_stream = self.text_processor.create_text_stream(texts)

            # 2. TTS 추론 실행
            tts_task, tts_data = await self.tts_processor.process_tts_inference(
                text_stream
            )

            # 3. 오디오 포워딩 실행
            output_results = []

            try:
                # 타임아웃을 적용하여 오디오 처리
                async with asyncio.timeout(timeout):
                    async for (
                        output_data
                    ) in self.audio_processor.process_audio_forwarding(
                        tts_data.audio_ch
                    ):
                        output_results.append(output_data)

                        # 진행 상황 로깅
                        if len(output_results) % 10 == 0:
                            logger.info(
                                f"📊 진행 상황: {len(output_results)}개 프레임 처리됨"
                            )

            except asyncio.TimeoutError:
                logger.warning(f"⏰ 파이프라인 타임아웃 ({timeout}초) - 부분 결과 반환")

            # 4. TTS 태스크 완료 대기 (추가 타임아웃 적용)
            try:
                async with asyncio.timeout(5.0):
                    await tts_task
            except asyncio.TimeoutError:
                logger.warning("⏰ TTS 태스크 완료 대기 타임아웃")
                tts_task.cancel()

            self.end_time = time.time()

            # 결과 통계 생성
            stats = self._generate_pipeline_stats(output_results)

            logger.info(
                f"🎉 전체 파이프라인 완료 - 총 시간: {stats['total_duration']:.2f}초"
            )
            return stats

        except Exception as e:
            self.end_time = time.time()
            logger.error(f"❌ 파이프라인 오류: {e}")
            raise PipelineError(f"파이프라인 처리 실패: {e}")

    def _generate_pipeline_stats(
        self, output_results: List[AudioOutputData]
    ) -> Dict[str, Any]:
        """파이프라인 통계 생성"""
        total_duration = (
            self.end_time - self.start_time if self.start_time and self.end_time else 0
        )

        successful_outputs = [r for r in output_results if r.success]
        failed_outputs = [r for r in output_results if not r.success]

        total_audio_duration = sum(r.duration for r in successful_outputs)

        stats = {
            # 전체 통계
            "total_duration": total_duration,
            "total_audio_duration": total_audio_duration,
            # 텍스트 처리 통계
            "processed_text_chunks": self.text_processor.processed_chunks,
            # TTS 통계
            "tts_provider": self.tts_processor.tts_provider.name,
            # 오디오 통계
            "audio_player": self.audio_processor.audio_player.name,
            "total_audio_frames": len(output_results),
            "successful_audio_frames": len(successful_outputs),
            "failed_audio_frames": len(failed_outputs),
            # 성능 지표
            "success_rate": len(successful_outputs) / len(output_results)
            if output_results
            else 0,
            "processing_speed": len(output_results) / total_duration
            if total_duration > 0
            else 0,
            # 오류 정보
            "errors": [r.error_message for r in failed_outputs if r.error_message],
            # 스트림 통계
            "stream_tees_created": self.stream_processor.tees_created,
        }

        return stats

    async def cleanup(self):
        """리소스 정리"""
        try:
            await self.tts_processor.tts_provider.cleanup()
            await self.audio_processor.audio_player.cleanup()
            logger.info("🧹 파이프라인 컴포넌트 정리 완료")
        except Exception as e:
            logger.error(f"❌ 파이프라인 정리 오류: {e}")


# 편의 함수들
async def create_component_processor(
    tts_provider: StreamingTTSProvider, audio_player: StreamingAudioPlayer
) -> PipelineComponentProcessor:
    """컴포넌트 프로세서 생성 및 초기화"""
    processor = PipelineComponentProcessor(tts_provider, audio_player)

    # 초기화 검증
    if not tts_provider.is_initialized:
        await tts_provider.initialize()

    if not audio_player.is_initialized:
        await audio_player.initialize()

    return processor


async def quick_pipeline_test(
    texts: List[str],
    tts_provider: StreamingTTSProvider,
    audio_player: StreamingAudioPlayer,
    timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """빠른 파이프라인 테스트"""
    processor = await create_component_processor(tts_provider, audio_player)

    try:
        return await processor.process_full_pipeline(texts, timeout)
    finally:
        await processor.cleanup()
