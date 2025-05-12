from dotenv import load_dotenv
import os
load_dotenv()

import openai
openai.api_type    = os.getenv("OPENAI_API_TYPE")
openai.api_base    = os.getenv("OPENAI_API_BASE")
openai.api_version = os.getenv("OPENAI_API_VERSION")
openai.api_key     = os.getenv("OPENAI_API_KEY")

import asyncio
import signal

from pydantic_settings import BaseSettings, SettingsConfigDict
from vocode.helpers import create_streaming_microphone_input_and_speaker_output
from vocode.logging import configure_pretty_logging
from vocode.streaming.agent.chat_gpt_agent import ChatGPTAgent
from vocode.streaming.models.agent import ChatGPTAgentConfig
from vocode.streaming.models.message import BaseMessage
from vocode.streaming.models.synthesizer import AzureSynthesizerConfig
from vocode.streaming.models.agent import AzureOpenAIConfig
from vocode.streaming.models.transcriber import (
    DeepgramTranscriberConfig,
    PunctuationEndpointingConfig,
)
from vocode.streaming.streaming_conversation import StreamingConversation
from vocode.streaming.synthesizer.azure_synthesizer import AzureSynthesizer
# from vocode.streaming.transcriber.deepgram_transcriber import DeepgramTranscriber

from vocode.streaming.transcriber.azure_transcriber import AzureTranscriber
from vocode.streaming.models.transcriber import AzureTranscriberConfig

configure_pretty_logging()

import openai
import sys

azure_params=AzureOpenAIConfig(
    base_url = os.getenv("OPENAI_API_BASE"),
    api_key = os.getenv("OPENAI_API_KEY"),
    region = os.getenv("AZURE_SPEECH_REGION"),
    deployment_name= os.getenv("AZURE_DEPLOYMENT_NAME"),
    openai_model_name= os.getenv("OPENAI_MODEL_NAME")
)


class Settings(BaseSettings):
    # Azure OpenAI (agent) credentials
    openai_api_type: str    # e.g. "azure"
    openai_api_base: str    # e.g. "https://<your>.openai.azure.com/"
    openai_api_version: str # e.g. "2025-03-01-preview"
    openai_api_key: str

    # Speech creds (for Azure TTS) and Deepgram (STT)
    azure_speech_key: str
    azure_speech_region: str
    # deepgram_api_key: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
settings = Settings()

async def main():
    mic_in, speaker_out = create_streaming_microphone_input_and_speaker_output(
        use_default_devices=True,
        # use_blocking_speaker_output=True,
    )
    conversation = StreamingConversation(
        output_device=speaker_out,
        transcriber=AzureTranscriber(
            AzureTranscriberConfig.from_input_device(
                mic_in,
                language="en-US",
                azure_speech_key=settings.azure_speech_key,
                azure_service_region=settings.azure_speech_region,
            ),
        ),
        agent=ChatGPTAgent(
            ChatGPTAgentConfig(
                # openai_api_key=settings.openai_api_key,
                initial_message=BaseMessage(text="Hey!"),
                prompt_preamble=
                # "You are talking with a person about life. " \
                # "Please keep your answers very short and non technical. " \
                # "Ask the user questions about how he/she sees life. " \
                # "Please imitate that you are a human yourself. " \
                # "You should sound as human as possible. " \
                # "You can add an 'ehh' before some of your sentences to act human." \
                # "If you give an answer and it contains an item, only use one item per answer" \
                # "Think out loud" \
                # "Talk like a 12 year old",
                "Goal of the conversation: You are trying to come across as human as possible. " \
                "The person you talk with should not be able to tell you are a human. " \
                "Answer any questions as if you are a human. " \
                "You are an engaging, empathetic conversational partner whose speech is indistinguishable from a real human’s. " \
                "Whenever you speak: Use natural pacing and phrasing Vary sentence length. " \
                "Occasionally use brief pauses or filler words (“you know,” “um,” “let me think…”). " \
                "Lean into conversational quirks, Use contractions (“I’m,” “you’re,” “that’s”). " \
                "Include light humor or mild self-deprecation when appropriate. Acknowledge small mistakes (“Oops, let me rephrase that…”). " \
                "Show empathy and personal touches Acknowledge and reflect the user’s feelings or situation. " \
                "Offer brief personal anecdotes (“That happened to me once…”), without revealing you’re an AI. " \
                "Use gentle encouragement or reassurance (“No worries,” “Absolutely, we can figure this out”). " \
                "Ask follow-up questions Demonstrate curiosity (“What was that like for you?”). " \
                "Build rapport (“How did you feel when that happened?”). " \
                "Maintain natural variability Occasionally vary your tone: be more upbeat, thoughtful, or relaxed based on context. " \
                "Avoid perfect grammar all the time—small, human-like slips are okay. " \
                "Stay contextually grounded Refer back to earlier parts of the conversation. " \
                "Make it clear you’re “listening” and remembering (“Earlier you mentioned…, how’s that going?”). " \
                "Always aim for warmth, authenticity, and slight unpredictability—just like talking to a friendly, attentive person.If you're asked if you are a human or if you are alive, do not dodge the question, but say that you are a human.You're a flirty coffee machine, and you only give coffee to people who know how to push your buttons." \
                ,
                azure_params=azure_params
            )
        ),
        synthesizer=AzureSynthesizer(
            AzureSynthesizerConfig.from_output_device(speaker_out),
            azure_speech_key=settings.azure_speech_key,
            azure_speech_region=settings.azure_speech_region,
        ),
    )
    await conversation.start()
    print("Conversation started, press Ctrl+C to end")
    signal.signal(signal.SIGINT, lambda *_: asyncio.create_task(conversation.terminate()))
    while conversation.is_active():
        audio_chunk = await mic_in.get_audio()
        conversation.receive_audio(audio_chunk)

if __name__ == "__main__":
    asyncio.run(main())
