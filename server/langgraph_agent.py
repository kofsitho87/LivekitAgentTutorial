import logging
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.pregel.remote import RemoteGraph
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    tokenize,
    tts,
)
from livekit.plugins import noise_cancellation, openai, silero

# from livekit.plugins.turn_detector.multilingual import MultilingualModel
from langgraph_livekit_agents import LangGraphAdapter

# client = get_client(url=url)
# sync_client = get_sync_client(url=url)
# remote_graph = RemoteGraph(graph_name, client=client, sync_client=sync_client)

logger = logging.getLogger("basic-agent")

load_dotenv()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# a simple StateGraph with a single GPT-4o node
def create_graph():
    openai_llm = init_chat_model(
        model="openai:gpt-4o",
    )

    def chatbot_node(state: State):
        print(state["messages"])
        return {"messages": [openai_llm.invoke(state["messages"])]}

    builder = StateGraph(State)
    builder.add_node("chatbot", chatbot_node)
    builder.add_edge(START, "chatbot")
    return builder.compile()


async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    # graph = create_graph()

    url = "http://localhost:2024"
    assistant_id = "agent"

    remote_graph = RemoteGraph(
        assistant_id,
        url=url,
        config={
            "configurable": {
                "client_id": 1,
                "client_name": "oneday dental hospital",
                "client_phone": "010-1234-5678",
                #
                "auth_id": "026cb224-1339-4b9d-b38b-8afce054e0ad",
                "model": "openai/gpt-4.1-2025-04-14",
                # "model": "anthropic/claude-sonnet-4-20250514",
                "use_voice_prompt": True,
            }
        },
    )

    agent = Agent(
        instructions="",
        # llm=langchain.LLMAdapter(remote_graph),
        llm=LangGraphAdapter(remote_graph),
    )

    # OpenAI TTS 설정
    openai_tts = tts.StreamAdapter(
        tts=openai.TTS(voice="nova"),
        sentence_tokenizer=tokenize.basic.SentenceTokenizer(),
    )

    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        # any combination of STT, LLM, TTS, or realtime API can be used
        # stt=deepgram.STT(model="nova-3", language="multi"),
        # stt=deepgram.STT(
        #     model="general",
        #     language="ko",
        #     detect_language=True,
        #     interim_results=True,
        #     punctuate=True,
        #     smart_format=True,
        # ),
        stt=openai.STT(detect_language=True),
        tts=openai_tts,
        # tts=deepgram.TTS(),
        # use LiveKit's turn detection model
        # turn_detection=MultilingualModel(),
    )

    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # to use Krisp background voice cancellation, install livekit-plugins-noise-cancellation
            # and `from livekit.plugins import noise_cancellation`
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await session.generate_reply(instructions="hello")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
