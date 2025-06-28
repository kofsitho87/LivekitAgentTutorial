"""
Pipeline Module
TTS 파이프라인 처리 및 조정 시스템
"""

# Core processor classes
# Pipeline coordinator
from .coordinator import (
    PipelineConfig,
    PipelineCoordinator,
    PipelineResult,
    batch_tts_pipeline,
    get_default_coordinator,
    quick_tts_pipeline,
)
from .processor import (
    AudioProcessor,
    PipelineComponentProcessor,
    StreamProcessor,
    TextStreamProcessor,
    TTSProcessor,
    create_component_processor,
    quick_pipeline_test,
)

# Default coordinator instance
_default_coordinator = None


# Convenience functions
def get_coordinator() -> PipelineCoordinator:
    """기본 파이프라인 조정자 반환"""
    return get_default_coordinator()


async def run_pipeline(
    texts,
    tts_provider: str = None,
    audio_player: str = None,
    timeout: float = None,
    enable_detailed_logging: bool = True,
) -> PipelineResult:
    """
    간단한 파이프라인 실행 인터페이스

    Args:
        texts: 처리할 텍스트 (문자열 또는 리스트)
        tts_provider: TTS 제공자 이름
        audio_player: 오디오 재생자 이름
        timeout: 타임아웃 (초)
        enable_detailed_logging: 상세 로깅 활성화

    Returns:
        PipelineResult: 실행 결과
    """
    config = PipelineConfig(
        tts_provider_name=tts_provider,
        audio_player_name=audio_player,
        timeout=timeout,
        enable_detailed_logging=enable_detailed_logging,
    )

    coordinator = get_coordinator()
    return await coordinator.execute_pipeline(texts, config)


async def run_batch_pipeline(
    text_batches,
    concurrent: bool = True,
    max_concurrency: int = 3,
    tts_provider: str = None,
    audio_player: str = None,
):
    """
    배치 파이프라인 실행 인터페이스

    Args:
        text_batches: 텍스트 배치 리스트
        concurrent: 동시 실행 여부
        max_concurrency: 최대 동시 실행 수
        tts_provider: TTS 제공자 이름
        audio_player: 오디오 재생자 이름

    Returns:
        List[PipelineResult]: 실행 결과 리스트
    """
    coordinator = get_coordinator()

    # 설정 생성
    config = PipelineConfig(
        tts_provider_name=tts_provider, audio_player_name=audio_player
    )

    # 요청 생성
    requests = [{"texts": texts, "config": config} for texts in text_batches]

    return await coordinator.execute_multiple_pipelines(
        requests, concurrent=concurrent, max_concurrency=max_concurrency
    )


async def get_pipeline_status():
    """파이프라인 시스템 상태 조회"""
    coordinator = get_coordinator()
    return await coordinator.get_system_status()


async def cleanup_pipeline():
    """파이프라인 시스템 정리"""
    coordinator = get_coordinator()
    await coordinator.cleanup_all()


# LiveKit 스타일 호환성 함수들
async def pipeline_reply_task(
    texts,
    tts_provider_name: str = None,
    audio_player_name: str = None,
    timeout: float = None,
):
    """
    LiveKit 스타일 파이프라인 응답 태스크

    Args:
        texts: 처리할 텍스트
        tts_provider_name: TTS 제공자 이름
        audio_player_name: 오디오 재생자 이름
        timeout: 타임아웃

    Returns:
        PipelineResult: 실행 결과
    """
    return await run_pipeline(
        texts=texts,
        tts_provider=tts_provider_name,
        audio_player=audio_player_name,
        timeout=timeout,
    )


# 고급 파이프라인 함수들
async def stream_pipeline(
    text_stream, tts_provider: str = None, audio_player: str = None
):
    """
    스트리밍 파이프라인 (향후 구현)

    Args:
        text_stream: 텍스트 스트림
        tts_provider: TTS 제공자
        audio_player: 오디오 재생자
    """
    # TODO: 실시간 스트리밍 파이프라인 구현
    raise NotImplementedError("스트리밍 파이프라인은 향후 구현 예정입니다")


def create_custom_pipeline(
    tts_provider_name: str, audio_player_name: str, custom_config: dict = None
) -> PipelineConfig:
    """
    커스텀 파이프라인 설정 생성

    Args:
        tts_provider_name: TTS 제공자 이름
        audio_player_name: 오디오 재생자 이름
        custom_config: 추가 설정

    Returns:
        PipelineConfig: 파이프라인 설정
    """
    config = PipelineConfig(
        tts_provider_name=tts_provider_name, audio_player_name=audio_player_name
    )

    if custom_config:
        for key, value in custom_config.items():
            if hasattr(config, key):
                setattr(config, key, value)

    return config


__all__ = [
    # Core processor classes
    "TextStreamProcessor",
    "TTSProcessor",
    "AudioProcessor",
    "StreamProcessor",
    "PipelineComponentProcessor",
    # Coordinator classes
    "PipelineConfig",
    "PipelineResult",
    "PipelineCoordinator",
    # Factory functions
    "create_component_processor",
    "create_custom_pipeline",
    # High-level interface functions
    "run_pipeline",
    "run_batch_pipeline",
    "get_pipeline_status",
    "cleanup_pipeline",
    # Convenience functions
    "get_coordinator",
    "get_default_coordinator",
    "quick_tts_pipeline",
    "batch_tts_pipeline",
    "quick_pipeline_test",
    # LiveKit compatibility
    "pipeline_reply_task",
    # Advanced functions (future)
    "stream_pipeline",
]
