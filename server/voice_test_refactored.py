#!/usr/bin/env python3
"""
Refactored Voice Test
새로운 모듈 구조를 사용하는 리팩터링된 음성 테스트 시스템

이 파일은 다음과 같은 새로운 아키텍처를 사용합니다:
- src.config: 설정 관리
- src.tts: TTS 제공자 추상화
- src.audio: 오디오 재생자 추상화
- src.pipeline: 파이프라인 조정 시스템
"""

import asyncio
import logging
import os
import sys
from typing import List, Optional

from dotenv import load_dotenv

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(__file__))

# 새로운 모듈 구조 import
from tts_sample.config.settings import get_logging_config
from tts_sample.pipeline import cleanup_pipeline, get_pipeline_status, run_pipeline

load_dotenv(override=True)


# 로깅 설정
def setup_logging():
    """로깅 시스템 설정"""
    log_config = get_logging_config()

    logging.basicConfig(
        level=getattr(logging, log_config.level),
        format=log_config.format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


logger = logging.getLogger(__name__)


class RefactoredVoiceTest:
    """리팩터링된 음성 테스트 클래스"""

    def __init__(self):
        self.test_texts = [
            "안녕하세요! 새로운 모듈 구조로 리팩터링된 TTS 시스템입니다.",
            "이 시스템은 다양한 TTS 제공자와 오디오 재생자를 지원합니다.",
            "OpenAI TTS, pygame 오디오, 그리고 시뮬레이션 모드를 제공합니다.",
            "LiveKit 아키텍처 패턴을 유지하면서 모듈화되었습니다.",
            "테스트가 성공적으로 완료되었습니다!",
        ]

    async def run_system_diagnostics(self):
        """시스템 진단 실행"""
        logger.info("🔍 시스템 진단 시작")

        try:
            # 1. 파이프라인 시스템 상태 확인
            status = await get_pipeline_status()
            logger.info("📊 파이프라인 시스템 상태:")
            logger.info(
                f"  - 조정자 상태: {status.get('coordinator_status', 'unknown')}"
            )
            logger.info(f"  - 활성 프로세서: {status.get('active_processors', 0)}개")

            # 2. TTS 제공자 상태 확인
            tts_status = status.get("tts_providers", {})
            available_tts = tts_status.get("available", [])
            total_tts = tts_status.get("total", [])

            logger.info("🔊 TTS 제공자 상태:")
            logger.info(f"  - 전체: {total_tts}")
            logger.info(f"  - 사용 가능: {available_tts}")

            # 3. 오디오 재생자 상태 확인
            audio_status = status.get("audio_players", {})
            available_audio = audio_status.get("available", [])
            total_audio = audio_status.get("total", [])

            logger.info("🔊 오디오 재생자 상태:")
            logger.info(f"  - 전체: {total_audio}")
            logger.info(f"  - 사용 가능: {available_audio}")

            # 4. 권장 설정 제안
            self._suggest_optimal_configuration(available_tts, available_audio)

            return status

        except Exception as e:
            logger.error(f"❌ 시스템 진단 실패: {e}")
            return None

    def _suggest_optimal_configuration(
        self, available_tts: List[str], available_audio: List[str]
    ):
        """최적 설정 제안"""
        logger.info("💡 권장 설정:")

        # TTS 제공자 우선순위
        tts_priority = ["openai", "simulator", "echo"]
        recommended_tts = None

        for tts in tts_priority:
            if tts in available_tts:
                recommended_tts = tts
                break

        # 오디오 재생자 우선순위
        audio_priority = ["pygame", "simulator", "logger", "null"]
        recommended_audio = None

        for audio in audio_priority:
            if audio in available_audio:
                recommended_audio = audio
                break

        if recommended_tts and recommended_audio:
            logger.info(f"  - TTS: {recommended_tts}")
            logger.info(f"  - Audio: {recommended_audio}")

            # 설정별 특징 안내
            if recommended_tts == "openai":
                logger.info("  ✨ 실제 OpenAI TTS 사용 (API 키 필요)")
            else:
                logger.info("  🎭 시뮬레이션 TTS 사용")

            if recommended_audio == "pygame":
                logger.info("  🎵 실제 오디오 재생 (pygame)")
            else:
                logger.info("  📝 시뮬레이션 오디오 재생")
        else:
            logger.warning("  ⚠️ 권장 설정을 찾을 수 없습니다")

    async def run_basic_test(
        self,
        tts_provider: Optional[str] = None,
        audio_player: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """기본 파이프라인 테스트"""
        logger.info("🚀 기본 파이프라인 테스트 시작")
        logger.info(
            f"🔧 설정: TTS={tts_provider or 'auto'}, Audio={audio_player or 'auto'}"
        )

        try:
            # 파이프라인 실행
            result = await run_pipeline(
                texts=self.test_texts,
                tts_provider=tts_provider,
                audio_player=audio_player,
                timeout=timeout,
                enable_detailed_logging=True,
            )

            # 결과 분석
            logger.info("📊 테스트 결과:")
            logger.info(f"  - 성공: {result.success}")
            logger.info(f"  - 실행 시간: {result.execution_time:.2f}초")
            logger.info(f"  - 처리된 텍스트: {result.processed_texts}개")
            logger.info(f"  - 생성된 오디오 프레임: {result.generated_audio_frames}개")
            logger.info(f"  - 성공한 오디오 프레임: {result.successful_audio_frames}개")
            logger.info(f"  - 실패한 오디오 프레임: {result.failed_audio_frames}개")

            if result.statistics:
                success_rate = result.statistics.get("success_rate", 0)
                processing_speed = result.statistics.get("processing_speed", 0)
                logger.info(f"  - 성공률: {success_rate:.1%}")
                logger.info(f"  - 처리 속도: {processing_speed:.1f} 프레임/초")

            # 사용된 제공자 정보
            logger.info("🔊 사용된 제공자:")
            logger.info(f"  - TTS: {result.tts_provider_used}")
            logger.info(f"  - Audio: {result.audio_player_used}")

            if not result.success:
                logger.error(f"❌ 테스트 실패: {result.error_message}")
            else:
                logger.info("✅ 기본 테스트 성공!")

            return result

        except Exception as e:
            logger.error(f"❌ 기본 테스트 오류: {e}")
            return None

    async def run_provider_comparison_test(self):
        """제공자별 성능 비교 테스트"""
        logger.info("🔬 제공자별 성능 비교 테스트 시작")

        try:
            # 사용 가능한 제공자 조회
            status = await get_pipeline_status()
            available_tts = status.get("tts_providers", {}).get("available", [])
            available_audio = status.get("audio_players", {}).get("available", [])

            results = {}
            test_text = "제공자별 성능 비교 테스트입니다."

            # TTS 제공자별 테스트
            for tts_provider in available_tts:
                logger.info(f"🧪 TTS 제공자 테스트: {tts_provider}")

                # 최적의 오디오 재생자 선택 (빠른 테스트를 위해)
                audio_player = (
                    "null" if "null" in available_audio else available_audio[0]
                )

                result = await run_pipeline(
                    texts=[test_text],
                    tts_provider=tts_provider,
                    audio_player=audio_player,
                    timeout=30.0,
                    enable_detailed_logging=False,
                )

                results[tts_provider] = {
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "audio_frames": result.generated_audio_frames,
                    "error": result.error_message if not result.success else None,
                }

            # 결과 보고
            logger.info("📊 제공자별 성능 비교 결과:")
            for provider, result in results.items():
                status_icon = "✅" if result["success"] else "❌"
                logger.info(
                    f"  {status_icon} {provider}: {result['execution_time']:.2f}초, {result['audio_frames']}프레임"
                )
                if result["error"]:
                    logger.info(f"    오류: {result['error']}")

            return results

        except Exception as e:
            logger.error(f"❌ 비교 테스트 오류: {e}")
            return None

    async def run_stress_test(self, concurrent_requests: int = 3):
        """스트레스 테스트"""
        logger.info(f"💪 스트레스 테스트 시작 - {concurrent_requests}개 동시 요청")

        try:
            # 동시 파이프라인 실행
            tasks = []
            for i in range(concurrent_requests):
                task = run_pipeline(
                    texts=[f"스트레스 테스트 요청 #{i + 1}입니다."],
                    tts_provider="simulator",  # 빠른 테스트를 위해 시뮬레이션 사용
                    audio_player="null",  # 빠른 테스트를 위해 null 사용
                    timeout=20.0,
                    enable_detailed_logging=False,
                )
                tasks.append(task)

            # 모든 요청 완료 대기
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 분석
            successful = 0
            failed = 0
            total_time = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"  ❌ 요청 #{i + 1}: {result}")
                    failed += 1
                else:
                    if result.success:
                        successful += 1
                        total_time += result.execution_time
                        logger.info(
                            f"  ✅ 요청 #{i + 1}: {result.execution_time:.2f}초"
                        )
                    else:
                        failed += 1
                        logger.error(f"  ❌ 요청 #{i + 1}: {result.error_message}")

            # 통계 보고
            logger.info("📊 스트레스 테스트 결과:")
            logger.info(f"  - 성공: {successful}/{concurrent_requests}")
            logger.info(f"  - 실패: {failed}/{concurrent_requests}")
            logger.info(f"  - 성공률: {successful / concurrent_requests:.1%}")
            if successful > 0:
                logger.info(f"  - 평균 처리 시간: {total_time / successful:.2f}초")

            return {
                "successful": successful,
                "failed": failed,
                "success_rate": successful / concurrent_requests,
                "average_time": total_time / successful if successful > 0 else 0,
            }

        except Exception as e:
            logger.error(f"❌ 스트레스 테스트 오류: {e}")
            return None


async def main():
    """메인 실행 함수"""
    setup_logging()
    logger.info("🎙️ 리팩터링된 음성 테스트 시스템 시작")

    test_system = RefactoredVoiceTest()

    try:
        # 1. 시스템 진단
        logger.info("\n" + "=" * 60)
        logger.info("1. 시스템 진단")
        logger.info("=" * 60)

        await test_system.run_system_diagnostics()

        # 2. 기본 테스트
        logger.info("\n" + "=" * 60)
        logger.info("2. 기본 파이프라인 테스트")
        logger.info("=" * 60)

        basic_result = await test_system.run_basic_test()

        if basic_result and basic_result.success:
            # 3. 제공자 비교 테스트
            logger.info("\n" + "=" * 60)
            logger.info("3. 제공자별 성능 비교")
            logger.info("=" * 60)

            await test_system.run_provider_comparison_test()

            # 4. 스트레스 테스트
            logger.info("\n" + "=" * 60)
            logger.info("4. 스트레스 테스트")
            logger.info("=" * 60)

            await test_system.run_stress_test()

        logger.info("\n" + "=" * 60)
        logger.info("🎉 모든 테스트 완료!")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.info("\n⚠️ 사용자에 의해 테스트가 중단되었습니다.")
    except Exception as e:
        logger.error(f"\n❌ 테스트 시스템 오류: {e}")
    finally:
        # 리소스 정리
        logger.info("🧹 리소스 정리 중...")
        await cleanup_pipeline()
        logger.info("✅ 정리 완료")


if __name__ == "__main__":
    # 환경 변수 설정 안내
    if not os.getenv("OPENAI_API_KEY"):
        print(
            "💡 팁: OPENAI_API_KEY 환경 변수를 설정하면 실제 OpenAI TTS를 테스트할 수 있습니다."
        )
        print("   현재는 시뮬레이션 모드로 실행됩니다.\n")

    # asyncio 실행
    asyncio.run(main())
