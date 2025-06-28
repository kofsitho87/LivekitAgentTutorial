"""
Channel and Streaming Utilities
LiveKit 스타일의 비동기 채널 및 스트림 분할 기능
"""

import asyncio
import logging
from collections.abc import AsyncIterable
from typing import List, TypeVar

from ..config.settings import get_channel_config

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Chan:
    """
    LiveKit aio.Chan 스타일의 비동기 채널 구현
    개선된 타임아웃 및 완료 신호 처리
    """

    def __init__(self, timeout: float = None):
        self._queue = asyncio.Queue()
        self._closed = False
        self._finished = False  # 데이터 전송 완료 플래그
        self._timeout = timeout or get_channel_config().timeout_seconds

    def send_nowait(self, item):
        """아이템을 큐에 즉시 추가"""
        if not self._closed:
            self._queue.put_nowait(item)

    async def send(self, item):
        """아이템을 큐에 비동기로 추가"""
        if not self._closed:
            await self._queue.put(item)

    def close(self):
        """채널 닫기"""
        self._closed = True
        self._finished = True

    def mark_finished(self):
        """데이터 전송 완료 마킹 (채널은 열어두되 더 이상 데이터 없음)"""
        self._finished = True

    @property
    def is_closed(self) -> bool:
        """채널이 닫혀있는지 확인"""
        return self._closed

    @property
    def is_finished(self) -> bool:
        """데이터 전송이 완료되었는지 확인"""
        return self._finished

    @property
    def size(self) -> int:
        """큐에 있는 아이템 수"""
        return self._queue.qsize()

    def __aiter__(self):
        return self

    async def __anext__(self):
        """비동기 이터레이터 구현"""
        while True:
            try:
                # 타임아웃을 길게 설정 (OpenAI API 호출 시간 고려)
                item = await asyncio.wait_for(self._queue.get(), timeout=self._timeout)
                return item
            except asyncio.TimeoutError:
                if self._finished and self._queue.empty():
                    raise StopAsyncIteration
                # 타임아웃이지만 아직 데이터가 올 수 있으면 계속 대기
                if not self._finished:
                    logger.debug("⏳ 채널 대기 중... (TTS 처리 중)")
                    continue
                else:
                    raise StopAsyncIteration


class StreamTee:
    """
    비동기 스트림을 여러 개로 분할하는 클래스
    LiveKit utils.aio.itertools.tee 기능 재현
    """

    def __init__(self, source: AsyncIterable[T], num_streams: int = None):
        self.source = source
        self.num_streams = num_streams or get_channel_config().tee_num_streams
        self.channels: List[Chan] = [Chan() for _ in range(self.num_streams)]
        self._task = None
        self._started = False

    def get_streams(self) -> List[AsyncIterable[T]]:
        """분할된 스트림들을 반환"""
        return self.channels

    async def start_tee(self):
        """Tee 프로세스 시작"""
        if not self._started:
            self._started = True
            self._task = asyncio.create_task(self._distribute_stream())

    async def _distribute_stream(self):
        """소스 스트림을 모든 채널에 분배"""
        logger.info(f"🔀 Stream Tee 시작 - 스트림을 {self.num_streams}개로 분할")

        try:
            async for item in self.source:
                logger.info(f"📤 Tee 분배: '{item}' -> {len(self.channels)}개 채널")

                # 모든 채널에 동일한 데이터 전송
                for i, channel in enumerate(self.channels):
                    channel.send_nowait(item)
                    logger.debug(f"  └─ 채널 {i + 1}에 전송")

        except Exception as e:
            logger.error(f"❌ Stream Tee 오류: {e}")
        finally:
            # 모든 채널에 완료 신호 전송
            for channel in self.channels:
                channel.mark_finished()
            logger.info("✅ Stream Tee 완료")

    async def stop(self):
        """Tee 프로세스 중지"""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # 모든 채널 닫기
        for channel in self.channels:
            channel.close()


async def create_channel_pair() -> tuple[Chan, Chan]:
    """채널 쌍 생성 (편의 함수)"""
    return Chan(), Chan()


async def tee_stream(
    source: AsyncIterable[T], num_streams: int = 2
) -> List[AsyncIterable[T]]:
    """
    스트림을 여러 개로 분할하는 편의 함수

    Args:
        source: 원본 스트림
        num_streams: 분할할 스트림 수

    Returns:
        분할된 스트림들의 리스트
    """
    tee = StreamTee(source, num_streams)
    await tee.start_tee()
    return tee.get_streams()
