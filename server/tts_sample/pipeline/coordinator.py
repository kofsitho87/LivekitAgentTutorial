"""
Pipeline Coordinator
전체 TTS 파이프라인 워크플로우를 관리하는 조정자
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from ..audio import AudioPlayerManager
from ..audio import get_player as get_audio_player
from ..core.exceptions import PipelineError
from ..tts import TTSProviderManager
from ..tts import get_provider as get_tts_provider
from .processor import PipelineComponentProcessor, create_component_processor

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """파이프라인 실행 설정"""

    tts_provider_name: Optional[str] = None
    audio_player_name: Optional[str] = None
    timeout: Optional[float] = None
    enable_statistics: bool = True
    enable_detailed_logging: bool = True
    auto_cleanup: bool = True

    # 고급 설정
    retry_count: int = 0
    retry_delay: float = 1.0
    partial_results: bool = True
    text_chunk_delay: float = 0.5  # 텍스트 청크 간 지연시간


@dataclass
class PipelineResult:
    """파이프라인 실행 결과"""

    success: bool
    statistics: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time: float = 0.0

    # 세부 결과
    processed_texts: int = 0
    generated_audio_frames: int = 0
    successful_audio_frames: int = 0
    failed_audio_frames: int = 0

    # 제공자 정보
    tts_provider_used: Optional[str] = None
    audio_player_used: Optional[str] = None


class PipelineCoordinator:
    """파이프라인 전체 조정자"""

    def __init__(
        self,
        tts_manager: Optional[TTSProviderManager] = None,
        audio_manager: Optional[AudioPlayerManager] = None,
    ):
        self.tts_manager = tts_manager
        self.audio_manager = audio_manager
        self.active_processors: List[PipelineComponentProcessor] = []

        # 실행 통계
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0

    async def execute_pipeline(
        self, texts: Union[str, List[str]], config: Optional[PipelineConfig] = None
    ) -> PipelineResult:
        """
        파이프라인 실행

        Args:
            texts: 처리할 텍스트 (문자열 또는 문자열 리스트)
            config: 파이프라인 설정

        Returns:
            PipelineResult: 실행 결과
        """
        if config is None:
            config = PipelineConfig()

        # 텍스트 정규화
        if isinstance(texts, str):
            text_list = [texts]
        else:
            text_list = texts

        if not text_list:
            return PipelineResult(
                success=False, error_message="처리할 텍스트가 없습니다"
            )

        self.total_executions += 1
        start_time = time.time()

        if config.enable_detailed_logging:
            logger.info(f"🚀 파이프라인 실행 #{self.total_executions} 시작")
            logger.info(f"📝 처리할 텍스트: {len(text_list)}개")
            logger.info(
                f"🔧 설정: TTS={config.tts_provider_name}, Audio={config.audio_player_name}"
            )

        try:
            # 재시도 로직
            for attempt in range(config.retry_count + 1):
                if attempt > 0:
                    logger.info(f"🔄 재시도 #{attempt}/{config.retry_count}")
                    await asyncio.sleep(config.retry_delay)

                try:
                    result = await self._execute_single_attempt(text_list, config)

                    if result.success or not config.partial_results:
                        break

                except Exception as e:
                    if attempt == config.retry_count:  # 마지막 시도
                        raise
                    else:
                        logger.warning(f"⚠️ 시도 #{attempt + 1} 실패: {e}")
                        continue

            # 실행 시간 계산
            result.execution_time = time.time() - start_time

            # 통계 업데이트
            if result.success:
                self.successful_executions += 1
            else:
                self.failed_executions += 1

            if config.enable_detailed_logging:
                logger.info(
                    f"✅ 파이프라인 실행 완료 - 시간: {result.execution_time:.2f}초"
                )
                logger.info(
                    f"📊 성공률: {self.successful_executions}/{self.total_executions}"
                )

            return result

        except Exception as e:
            self.failed_executions += 1
            execution_time = time.time() - start_time

            error_msg = f"파이프라인 실행 실패: {e}"
            logger.error(f"❌ {error_msg}")

            return PipelineResult(
                success=False, error_message=error_msg, execution_time=execution_time
            )

    async def _execute_single_attempt(
        self, text_list: List[str], config: PipelineConfig
    ) -> PipelineResult:
        """단일 파이프라인 실행 시도"""

        # 1. TTS 제공자 선택
        try:
            if self.tts_manager:
                tts_provider = self.tts_manager.get_provider(config.tts_provider_name)
            else:
                tts_provider = get_tts_provider(config.tts_provider_name)

            logger.info(f"🔊 TTS 제공자: {tts_provider.name}")

        except Exception as e:
            raise PipelineError(f"TTS 제공자 선택 실패: {e}")

        # 2. 오디오 재생자 선택
        try:
            if self.audio_manager:
                audio_player = self.audio_manager.get_player(config.audio_player_name)
            else:
                audio_player = get_audio_player(config.audio_player_name)

            logger.info(f"🔊 오디오 재생자: {audio_player.name}")

        except Exception as e:
            raise PipelineError(f"오디오 재생자 선택 실패: {e}")

        # 3. 컴포넌트 프로세서 생성
        processor = await create_component_processor(tts_provider, audio_player)
        self.active_processors.append(processor)

        try:
            # 4. 파이프라인 실행
            stats = await processor.process_full_pipeline(text_list, config.timeout)

            # 5. 결과 생성
            result = PipelineResult(
                success=True,
                statistics=stats if config.enable_statistics else {},
                processed_texts=stats.get("processed_text_chunks", 0),
                generated_audio_frames=stats.get("total_audio_frames", 0),
                successful_audio_frames=stats.get("successful_audio_frames", 0),
                failed_audio_frames=stats.get("failed_audio_frames", 0),
                tts_provider_used=tts_provider.name,
                audio_player_used=audio_player.name,
            )

            return result

        finally:
            # 6. 정리
            if config.auto_cleanup:
                await processor.cleanup()
                if processor in self.active_processors:
                    self.active_processors.remove(processor)

    async def execute_multiple_pipelines(
        self,
        pipeline_requests: List[Dict[str, Any]],
        concurrent: bool = False,
        max_concurrency: int = 3,
    ) -> List[PipelineResult]:
        """
        여러 파이프라인 동시 또는 순차 실행

        Args:
            pipeline_requests: 파이프라인 요청 리스트
                [{"texts": [...], "config": PipelineConfig}, ...]
            concurrent: 동시 실행 여부
            max_concurrency: 최대 동시 실행 수

        Returns:
            List[PipelineResult]: 실행 결과 리스트
        """
        logger.info(f"🚀 다중 파이프라인 실행: {len(pipeline_requests)}개 요청")

        if concurrent:
            # 동시 실행
            semaphore = asyncio.Semaphore(max_concurrency)

            async def execute_with_semaphore(request):
                async with semaphore:
                    return await self.execute_pipeline(
                        request.get("texts", []), request.get("config")
                    )

            tasks = [execute_with_semaphore(req) for req in pipeline_requests]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 예외 처리
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(
                        PipelineResult(
                            success=False,
                            error_message=f"파이프라인 #{i} 실행 실패: {result}",
                        )
                    )
                else:
                    processed_results.append(result)

            return processed_results

        else:
            # 순차 실행
            results = []
            for i, request in enumerate(pipeline_requests):
                logger.info(
                    f"📋 파이프라인 #{i + 1}/{len(pipeline_requests)} 실행 중..."
                )

                result = await self.execute_pipeline(
                    request.get("texts", []), request.get("config")
                )
                results.append(result)

            return results

    async def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        try:
            # TTS 제공자 상태
            if self.tts_manager:
                available_tts = self.tts_manager.get_available_providers()
                all_tts = self.tts_manager.list_providers()
            else:
                from ..tts import get_default_manager

                tts_mgr = get_default_manager()
                available_tts = tts_mgr.get_available_providers()
                all_tts = tts_mgr.list_providers()

            # 오디오 재생자 상태
            if self.audio_manager:
                available_audio = self.audio_manager.get_available_players()
                all_audio = self.audio_manager.list_players()
            else:
                from ..audio import get_available_players, get_default_manager

                available_audio = get_available_players()
                audio_mgr = get_default_manager()
                all_audio = audio_mgr.list_players()

            return {
                "coordinator_status": "active",
                "active_processors": len(self.active_processors),
                "execution_stats": {
                    "total": self.total_executions,
                    "successful": self.successful_executions,
                    "failed": self.failed_executions,
                    "success_rate": self.successful_executions / self.total_executions
                    if self.total_executions > 0
                    else 0,
                },
                "tts_providers": {"available": available_tts, "total": all_tts},
                "audio_players": {"available": available_audio, "total": all_audio},
            }

        except Exception as e:
            logger.error(f"❌ 시스템 상태 조회 실패: {e}")
            return {"coordinator_status": "error", "error": str(e)}

    async def cleanup_all(self):
        """모든 활성 프로세서 정리"""
        logger.info(f"🧹 활성 프로세서 정리: {len(self.active_processors)}개")

        cleanup_tasks = []
        for processor in self.active_processors[:]:
            cleanup_tasks.append(processor.cleanup())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self.active_processors.clear()
        logger.info("✅ 모든 프로세서 정리 완료")


# 전역 조정자 인스턴스
_default_coordinator = None


def get_default_coordinator() -> PipelineCoordinator:
    """기본 파이프라인 조정자 반환"""
    global _default_coordinator
    if _default_coordinator is None:
        _default_coordinator = PipelineCoordinator()
    return _default_coordinator


# 편의 함수들
async def quick_tts_pipeline(
    texts: Union[str, List[str]],
    tts_provider: str = None,
    audio_player: str = None,
    timeout: float = None,
) -> PipelineResult:
    """빠른 TTS 파이프라인 실행"""
    coordinator = get_default_coordinator()

    config = PipelineConfig(
        tts_provider_name=tts_provider, audio_player_name=audio_player, timeout=timeout
    )

    return await coordinator.execute_pipeline(texts, config)


async def batch_tts_pipeline(
    text_batches: List[List[str]], concurrent: bool = True, max_concurrency: int = 3
) -> List[PipelineResult]:
    """배치 TTS 파이프라인 실행"""
    coordinator = get_default_coordinator()

    requests = [{"texts": texts} for texts in text_batches]

    return await coordinator.execute_multiple_pipelines(
        requests, concurrent=concurrent, max_concurrency=max_concurrency
    )
