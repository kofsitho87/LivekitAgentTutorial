"""
TTS (Text-to-Speech) Module
다양한 TTS 엔진을 지원하는 통합 TTS 시스템
"""

# Base classes and interfaces
from .base import StreamingTTSProvider, TTSProvider, TTSProviderManager

# Concrete implementations
from .openai_tts import OpenAITTSProvider, create_openai_tts, quick_tts
from .simulator import (
    EchoTTSProvider,
    SimulatorTTSProvider,
    create_echo_tts,
    create_simulator_tts,
    quick_simulation,
)

# Default provider manager instance
_default_manager = TTSProviderManager()


# Convenience functions for quick setup
def setup_default_providers():
    """기본 TTS 제공자들을 설정"""
    # 시뮬레이션 제공자는 항상 사용 가능
    _default_manager.register_provider("simulator", create_simulator_tts())
    _default_manager.register_provider("echo", create_echo_tts())

    # OpenAI 제공자는 API 키가 있을 때만 등록
    openai_provider = create_openai_tts()
    if openai_provider.is_available():
        _default_manager.register_provider("openai", openai_provider)


def get_default_manager() -> TTSProviderManager:
    """기본 TTS 관리자 반환"""
    return _default_manager


def get_provider(name: str = None) -> TTSProvider:
    """TTS 제공자 반환"""
    return _default_manager.get_provider(name)


async def initialize_providers():
    """모든 제공자 초기화"""
    return await _default_manager.initialize_all()


async def cleanup_providers():
    """모든 제공자 정리"""
    await _default_manager.cleanup_all()


# 모듈 로드 시 기본 제공자 설정
setup_default_providers()

__all__ = [
    # Base classes
    "TTSProvider",
    "StreamingTTSProvider",
    "TTSProviderManager",
    # Implementations
    "OpenAITTSProvider",
    "SimulatorTTSProvider",
    "EchoTTSProvider",
    # Factory functions
    "create_openai_tts",
    "create_simulator_tts",
    "create_echo_tts",
    # Quick functions
    "quick_tts",
    "quick_simulation",
    # Module functions
    "setup_default_providers",
    "get_default_manager",
    "get_provider",
    "initialize_providers",
    "cleanup_providers",
]
