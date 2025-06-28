"""
Audio Module
다양한 오디오 재생 엔진을 지원하는 통합 오디오 시스템
"""

# Base classes and interfaces
from .base import (
    AudioPlayer,
    AudioPlayerManager,
    StreamingAudioPlayer,
    perform_audio_forwarding_with_player,
)

# Concrete implementations
from .pygame_player import (
    PygameAudioPlayer,
    create_pygame_player,
    is_pygame_available,
    quick_play_with_pygame,
)
from .simulator import (
    LogAudioPlayer,
    NullAudioPlayer,
    SimulatorAudioPlayer,
    create_log_player,
    create_null_player,
    create_simulator_player,
    quick_simulate_play,
)

# Default player manager instance
_default_manager = AudioPlayerManager()


# Convenience functions for quick setup
def setup_default_players():
    """기본 오디오 재생자들을 설정"""
    # 시뮬레이션 재생자들은 항상 사용 가능
    _default_manager.register_player("simulator", create_simulator_player())
    _default_manager.register_player("logger", create_log_player())
    _default_manager.register_player("null", create_null_player())

    # pygame 재생자는 라이브러리가 있을 때만 등록
    if is_pygame_available():
        _default_manager.register_player("pygame", create_pygame_player())


def get_default_manager() -> AudioPlayerManager:
    """기본 오디오 관리자 반환"""
    return _default_manager


def get_player(name: str = None) -> AudioPlayer:
    """오디오 재생자 반환"""
    return _default_manager.get_player(name)


async def initialize_players():
    """모든 재생자 초기화"""
    return await _default_manager.initialize_all()


async def cleanup_players():
    """모든 재생자 정리"""
    await _default_manager.cleanup_all()


def get_available_players():
    """사용 가능한 재생자 목록 반환"""
    return _default_manager.get_available_players()


# LiveKit 스타일 호환성 함수들
async def perform_audio_forwarding(audio_input, player_name: str = None):
    """
    LiveKit 스타일 오디오 포워딩 함수

    Args:
        audio_input: 오디오 프레임 스트림
        player_name: 사용할 재생자 이름 (None이면 기본 재생자)
    """
    player = get_player(player_name)
    if not isinstance(player, StreamingAudioPlayer):
        raise ValueError(f"재생자 '{player.name}'는 스트리밍을 지원하지 않습니다")

    async for output_data in player.perform_audio_forwarding(audio_input):
        yield output_data


# 편의 함수들
async def quick_play(audio_data: bytes, player_name: str = None) -> bool:
    """빠른 오디오 재생"""
    player = get_player(player_name)

    if not player.is_initialized:
        await player.initialize()

    try:
        return await player.play_audio_data(audio_data)
    finally:
        # 일회성 재생의 경우 정리하지 않음 (재사용을 위해)
        pass


def detect_best_player() -> str:
    """사용 가능한 최적의 재생자 감지"""
    available = get_available_players()

    # 우선순위: pygame > simulator > logger > null
    priority_order = ["pygame", "simulator", "logger", "null"]

    for player_name in priority_order:
        if player_name in available:
            return player_name

    # 폴백: 첫 번째 사용 가능한 재생자
    return available[0] if available else "null"


# 모듈 로드 시 기본 재생자 설정
setup_default_players()

__all__ = [
    # Base classes
    "AudioPlayer",
    "StreamingAudioPlayer",
    "AudioPlayerManager",
    # Implementations
    "PygameAudioPlayer",
    "SimulatorAudioPlayer",
    "LogAudioPlayer",
    "NullAudioPlayer",
    # Factory functions
    "create_pygame_player",
    "create_simulator_player",
    "create_log_player",
    "create_null_player",
    # Quick functions
    "quick_play_with_pygame",
    "quick_simulate_play",
    "quick_play",
    # Utility functions
    "is_pygame_available",
    "detect_best_player",
    # Module functions
    "setup_default_players",
    "get_default_manager",
    "get_player",
    "get_available_players",
    "initialize_players",
    "cleanup_players",
    # LiveKit compatibility
    "perform_audio_forwarding",
    "perform_audio_forwarding_with_player",
]
