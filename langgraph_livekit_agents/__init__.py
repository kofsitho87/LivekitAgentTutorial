"""
LangGraphAdapter masquerades as an livekit.LLM and translates the LiveKit chat chunks
into LangGraph messages.
"""

import logging
import uuid
from typing import Any, Dict, Optional

from httpx import HTTPStatusError
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessageChunk,
    HumanMessage,
    SystemMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphInterrupt
from langgraph.pregel import PregelProtocol
from langgraph.types import Command
from livekit.agents import llm
from livekit.agents.llm import ToolChoice
from livekit.agents.llm.chat_context import ChatContext, ChatMessage
from livekit.agents.llm.tool_context import FunctionTool, RawFunctionTool
from livekit.agents.tts import SynthesizeStream
from livekit.agents.types import (
    DEFAULT_API_CONNECT_OPTIONS,
    NOT_GIVEN,
    APIConnectOptions,
    NotGivenOr,
)
from livekit.agents.utils import shortuuid
from livekit.plugins.langchain.langgraph import LLMAdapter

logger = logging.getLogger(__name__)


# https://github.com/livekit/agents/issues/1370#issuecomment-2588821571
class FlushSentinel(str, SynthesizeStream._FlushSentinel):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)


class LangGraphStream(llm.LLMStream):
    def __init__(
        self,
        llm: LLMAdapter,
        *,
        chat_ctx: ChatContext,
        tools: list[FunctionTool | RawFunctionTool],
        conn_options: APIConnectOptions,
        graph: PregelProtocol,
        config: RunnableConfig | None = None,
    ):
        super().__init__(
            llm,
            chat_ctx=chat_ctx,
            tools=tools,
            conn_options=conn_options,
        )
        self._graph = graph
        self._config = config

    async def _run(self) -> None:
        # print("######### RUN #########")
        state = self._chat_ctx_to_state()

        async for message_chunk, _ in self._graph.astream(
            state,
            self._config,
            stream_mode="messages",
        ):
            chat_chunk = _to_chat_chunk(message_chunk)
            if chat_chunk:
                self._event_ch.send_nowait(chat_chunk)

    def _chat_ctx_to_state(self) -> dict[str, Any]:
        """Convert chat context to langgraph input"""

        messages: list[AIMessage | HumanMessage | SystemMessage] = []
        for item in self._chat_ctx.items:
            # only support chat messages, ignoring tool calls
            if isinstance(item, ChatMessage):
                content = item.text_content
                if content:
                    if item.role == "assistant":
                        messages.append(AIMessage(content=content))
                    elif item.role == "user":
                        messages.append(HumanMessage(content=content))
                    elif item.role in ["system", "developer"]:
                        messages.append(SystemMessage(content=content))

        return {
            "messages": messages,
        }

    async def _get_interrupt(cls) -> Optional[str]:
        try:
            state = await cls._graph.aget_state(config=cls._llm._config)
            interrupts = [
                interrupt for task in state.tasks for interrupt in task.interrupts
            ]
            assistant = next(
                (
                    interrupt
                    for interrupt in reversed(interrupts)
                    if isinstance(interrupt.value, str)
                ),
                None,
            )
            return assistant
        except HTTPStatusError:
            return None

    def _to_message(cls, msg: llm.ChatMessage) -> HumanMessage:
        if isinstance(msg.content, str):
            content = msg.content
        elif isinstance(msg.content, list):
            content = []
            for c in msg.content:
                if isinstance(c, str):
                    content.append({"type": "text", "text": c})
                elif isinstance(c, llm.ChatImage):
                    if isinstance(c.image, str):
                        content.append({"type": "image_url", "image_url": c.image})
                    else:
                        logger.warning("Unsupported image type")
                else:
                    logger.warning("Unsupported content type")
        else:
            content = ""

        return HumanMessage(content=content, id=msg.id)

    @staticmethod
    def _create_livekit_chunk(
        content: str,
        *,
        id: str | None = None,
    ) -> llm.ChatChunk | None:
        return llm.ChatChunk(
            request_id=id or shortuuid(),
            choices=[
                llm.Choice(delta=llm.ChoiceDelta(role="assistant", content=content))
            ],
        )

    @staticmethod
    async def _to_livekit_chunk(
        msg: BaseMessageChunk | str | None,
    ) -> llm.ChatChunk | None:
        if not msg:
            return None

        request_id = None
        content = msg

        if isinstance(msg, str):
            content = msg
        elif hasattr(msg, "content") and isinstance(msg.content, str):
            request_id = getattr(msg, "id", None)
            content = msg.content
        elif isinstance(msg, dict):
            request_id = msg.get("id")
            content = msg.get("content")

        return LangGraphStream._create_livekit_chunk(content, id=request_id)


class LangGraphAdapter(llm.LLM):
    def __init__(self, graph: PregelProtocol, *, config: RunnableConfig | None = None):
        super().__init__()
        self._graph = graph
        self._config = config

    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: list[FunctionTool | RawFunctionTool] | None = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        # these are unused, since tool execution takes place in langgraph
        parallel_tool_calls: NotGivenOr[bool] = NOT_GIVEN,
        tool_choice: NotGivenOr[ToolChoice] = NOT_GIVEN,
        extra_kwargs: NotGivenOr[dict[str, Any]] = NOT_GIVEN,
    ) -> llm.LLMStream:
        return LangGraphStream(
            self,
            chat_ctx=chat_ctx,
            tools=tools or [],
            graph=self._graph,
            conn_options=conn_options,
            config=self._config,
        )


def _to_chat_chunk(msg: str | Any) -> llm.ChatChunk | None:
    message_id = shortuuid("LC_")
    content: str | None = None

    if isinstance(msg, str):
        content = msg
    elif isinstance(msg, BaseMessageChunk):
        content = msg.text()
        if msg.id:
            message_id = msg.id
    elif isinstance(msg, dict):
        msg_type = msg.get("type")
        if msg.get("content") and msg_type != "tool":
            content = msg.get("content")
            if msg.get("id"):
                message_id = msg.get("id")

    if not content:
        return None

    return llm.ChatChunk(
        id=message_id,
        delta=llm.ChoiceDelta(
            role="assistant",
            content=content,
        ),
    )


def shortuuid(prefix: str = "") -> str:
    return prefix + str(uuid.uuid4().hex)[:12]
