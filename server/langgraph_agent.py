import logging
import os
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
from livekit.plugins import noise_cancellation, openai, silero, deepgram

from livekit.plugins.turn_detector.multilingual import MultilingualModel
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

    # wait for the first participant to arrive
    participant = await ctx.wait_for_participant()

    participant_name = participant.name
    participant_name_split = participant_name.split("_")
    client_id = participant_name_split[0]
    client_name = participant_name_split[1]
    client_phone = participant_name_split[2]
    client_address = participant_name_split[3]
    site_id = participant_name_split[4]


    print("participant")
    print(participant)
    # print(participant.name)
    # print(participant.attributes)
    # print(participant.metadata)

    print("########################")
    print(ctx.job)

    # metadata = json.loads(ctx.job.metadata)

    # customize behavior based on the participant
    # print(f"connected to room {ctx.room.name} with participant {ctx.participant}")
    print(f"connected to room {ctx.room.name}")

    # await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    url = os.getenv("LANGGRAPH_AGENT_URL", "http://localhost:2024")
    assistant_id = os.getenv("LANGGRAPH_AGENT_ID", "agent")

    remote_graph = RemoteGraph(
        assistant_id,
        url=url,
        config={
            "configurable": {
                "client_id": client_id,
                "client_name": client_name,
                "client_phone": client_phone,
                "client_address": client_address,
                "site_id": site_id,
                #
                "auth_id": "026cb224-1339-4b9d-b38b-8afce054e0ad",
                "model": "openai/gpt-4.1-2025-04-14",
                # "model": "openai/gpt-4o",
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

    stt = openai.STT(language="ko", detect_language=True)
    # stt = deepgram.STT(model="nova-3", language="multi")
    # stt = deepgram.STT(
    #     model="general",
    #     language="ko",
    #     detect_language=False,
    #     interim_results=True,
    #     punctuate=True,
    #     smart_format=True,
    # )
    
    # stt = deepgram.STT()

    # OpenAI TTS 설정
    openai_tts = tts.StreamAdapter(
        tts=openai.TTS(voice="nova"),
        sentence_tokenizer=tokenize.basic.SentenceTokenizer(),
    )

    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        # any combination of STT, LLM, TTS, or realtime API can be used
        # stt=deepgram.STT(model="nova-3", language="multi"),
        
        stt=stt,
        # tts=deepgram.TTS(),
        tts=openai_tts,
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
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm, agent_name="agent"))
