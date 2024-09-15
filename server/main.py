import asyncio
import logging
from livekit import rtc
from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
    tts,
    tokenize,
    llm,
    JobProcess,
    AutoSubscribe
)
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import deepgram, openai, silero
from dotenv import load_dotenv

import os
from supabase import create_client, Client

# 환경 변수 로드
load_dotenv()

logger = logging.getLogger("voice-assistant")

# Supabase 클라이언트 생성
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 프로세스 사전 준비 함수
def prewarm_process(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()  # 음성 활동 감지기(VAD) 로드

# 메인 엔트리포인트 함수
async def entrypoint(ctx: JobContext):
    chat_context = llm.ChatContext().append(
        role="system",
        text=(
            "You are a voice assistant created by LiveKit. Your interface with users will be voice. "
            "You should use short and concise responses, and avoiding usage of unpronouncable punctuation."
        ),
    )

    # OpenAI TTS 설정
    openai_tts = tts.StreamAdapter(
        tts=openai.TTS(voice="nova"),
        sentence_tokenizer=tokenize.basic.SentenceTokenizer(),
    )

    # LiveKit 룸에 연결
    # AutoSubscribe.SUBSCRIBE_ALL: 모든 트랙(오디오 및 비디오)을 자동으로 구독합니다.
    # AutoSubscribe.SUBSCRIBE_NONE: 모든 트랙을 구독하지 않습니다.
    # AutoSubscribe.AUDIO_ONLY: 오디오 트랙만 구독합니다.
    # AutoSubscribe.VIDEO_ONLY: 비디오 트랙만 구독합니다.
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)

    # 음성 비서 설정
    assistant = VoiceAssistant(
        vad=ctx.proc.userdata["vad"],  # Voice Activity Detection: 음성 활동 감지기
        stt=deepgram.STT(),  # Speech-to-Text: 음성을 텍스트로 변환하는 Deepgram STT 모델
        llm=openai.LLM(model="gpt-4o"),  # Language Model: GPT-4를 사용하는 OpenAI 언어 모델
        tts=openai_tts,  # Text-to-Speech: 텍스트를 음성으로 변환하는 OpenAI TTS 모델
        chat_ctx=chat_context,  # Chat Context: 대화 컨텍스트를 저장하는 객체
        interrupt_min_words=2,  # 최소 인터럽트 단어 수: 사용자 발화를 인터럽트하기 위한 최소 단어 수
        allow_interruptions=True,  # 인터럽트 허용: 사용자의 발화를 중간에 끊을 수 있는지 여부
    )

    assistant.start(ctx.room)  # 음성 비서 시작

    # 채팅 관리자 설정
    chat = rtc.ChatManager(ctx.room)

    # 텍스트로부터 답변 생성 함수
    async def answer_from_text(txt: str):
        chat_ctx = assistant.chat_ctx.copy()
        chat_ctx.append(role="user", text=txt)
        stream = assistant.llm.chat(chat_ctx=chat_ctx)
        await assistant.say(stream, allow_interruptions=True)

    # 사용자 음성 커밋 이벤트 핸들러
    @assistant.on("user_speech_committed")
    def on_user_speech_committed(msg: llm.ChatMessage):
        print(f"USER: {msg.content}")
        # User 메시지 저장 example
        # supabase.table("messages").insert({
        #     "room_name": ctx.room.name,
        #     "role": "user",
        #     "message": msg.content
        # }).execute()

    # 에이전트 음성 커밋 이벤트 핸들러
    @assistant.on("agent_speech_committed")
    def on_agent_speech_committed(msg: llm.ChatMessage):
        print(f"AGENT: {msg.content}")
        # Agent 메시지 저장 example
        # supabase.table("messages").insert({
        #     "room_name": ctx.room.name,
        #     "role": "agent",
        #     "message": msg.content
        # }).execute()

    # 채팅 메시지 수신 이벤트 핸들러
    @chat.on("message_received")
    def on_chat_received(msg: rtc.ChatMessage):
        if msg.message:
            asyncio.create_task(answer_from_text(msg.message))


# 메인 함수 실행
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,  # 엔트리포인트 함수 설정
            prewarm_fnc=prewarm_process,  # 사전 준비 함수 설정
        )
    )