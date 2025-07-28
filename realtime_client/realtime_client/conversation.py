import os
import json
import base64
import asyncio
from types import SimpleNamespace
from contextlib import asynccontextmanager
from typing import Any, Callable, Awaitable, cast

import websockets
import sounddevice as sd
from openai import AsyncAzureOpenAI
from openai.resources.beta.realtime.realtime import AsyncRealtimeConnection

from .audio_util import CHANNELS, SAMPLE_RATE, AudioPlayerAsync

class ConversationManager:
    """Manages a real-time audio conversation with a proxy."""

    class _WebSocketProxyConnection:
        """Mimics the real OpenAI connection object to route traffic via our proxy."""
        def __init__(self, websocket: websockets.WebSocketClientProtocol):
            self._websocket = websocket
            self._queue = asyncio.Queue()
            self._listener_task = asyncio.create_task(self._listen())
            self.session = SimpleNamespace(update=self._send_session_update)
            self.input_audio_buffer = SimpleNamespace(append=self._send_audio_append)

        async def _listen(self):
            try:
                async for message in self._websocket:
                    await self._queue.put(SimpleNamespace(**json.loads(message)))
            except websockets.exceptions.ConnectionClosed: pass

        async def _send_session_update(self, session: dict):
            await self.send({"type": "session.update", "session": session})

        async def _send_audio_append(self, audio: str):
            await self.send({"type": "input_audio_buffer.append", "audio": audio})

        async def send(self, data: dict):
            await self._websocket.send(json.dumps(data))

        async def __aiter__(self):
            while not self._listener_task.done():
                try: yield await self._queue.get()
                except asyncio.CancelledError: break

        async def aclose(self):
            self._listener_task.cancel()
            await self._websocket.close()

    @classmethod
    async def start_proxied_conversation(
        cls,
        proxy_url: str,
        duration_seconds: int,
        *,
        on_transcript_update: Callable[[str], Awaitable[None] | None] | None = None,
        input_device: int | None = None,
        output_device: int | None = None,
    ):
        """Starts a proxied conversation, patching the OpenAI client to use the proxy URL."""
        @asynccontextmanager
        async def _proxied_connect(self, model: str):
            async with websockets.connect(proxy_url) as websocket:
                proxy_conn = ConversationManager._WebSocketProxyConnection(websocket)
                try: yield proxy_conn
                finally: await proxy_conn.aclose()

        class _PatchedRealtime: connect = _proxied_connect
        class _PatchedBeta: realtime = _PatchedRealtime()
        AsyncAzureOpenAI.beta = _PatchedBeta

        manager = cls(
            on_transcript_update=on_transcript_update,
            input_device=input_device,
            output_device=output_device,
        )
        await manager._run_lifecycle(duration_seconds)

    def __init__(
        self,
        *,
        on_transcript_update: Callable[[str], Awaitable[None] | None] | None = None,
        input_device: int | None = None,
        output_device: int | None = None,
    ):
        self.on_transcript_update = on_transcript_update

        # dummy client for monkey patch
        self.client = AsyncAzureOpenAI(
            api_key="dummy_key",  
            azure_endpoint="https://dummy.com",
            api_version="2024-01-01" 
        )
        self.audio_player = AudioPlayerAsync(device=output_device)
        self.input_device = input_device

        self.connection: AsyncRealtimeConnection | None = None
        self.connected = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        self._acc_transcripts: dict[str, str] = {}
        self._last_audio_item_id: str | None = None

    async def _run_lifecycle(self, duration_seconds: int):
        """Manages the conversation lifecycle, including connection and audio handling."""
        try:
            self._tasks.append(asyncio.create_task(self._handle_realtime_connection()))
            self._tasks.append(asyncio.create_task(self._send_mic_audio()))

            await asyncio.wait_for(self.connected.wait(), timeout=10)
            print("Connection established. Audio is live.")
            
            await asyncio.sleep(duration_seconds)
            print(f"\n{duration_seconds}s timer expired. Ending conversation.")

        except asyncio.TimeoutError:
            print("Error: Connection to the proxy server timed out.")
        except Exception as e:
            print(f"An error occurred during the conversation: {e}")
        finally:
            self._stop()
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self.audio_player.terminate()
            print("Conversation finished.")

    def _stop(self):
        """Cancels all running background tasks."""
        for task in self._tasks:
            task.cancel()

    async def _handle_realtime_connection(self):
        """Manages the WebSocket connection and processes events."""
        try:
            async with self.client.beta.realtime.connect(model="dummy-deployment") as conn:
                self.connection = conn
                self.connected.set()
                await conn.session.update(session={"turn_detection": {"type": "server_vad"}})

                async for event in conn:
                    if event.type == "input_audio_buffer.speech_started":
                        await conn.send({"type": "response.cancel"})
                        self.audio_player.stop()
                    elif event.type == "response.audio.delta":
                        if event.item_id != self._last_audio_item_id:
                            self._last_audio_item_id = event.item_id
                        self.audio_player.add_data(base64.b64decode(event.delta))
                    elif event.type == "response.audio_transcript.delta":
                        text = self._acc_transcripts.get(event.item_id, "")
                        self._acc_transcripts[event.item_id] = text + event.delta
                        if self.on_transcript_update:
                            res = self.on_transcript_update(self._acc_transcripts[event.item_id])
                            if asyncio.iscoroutine(res):
                                await res

        except asyncio.CancelledError:
            pass

    async def _send_mic_audio(self):
        """Captures and sends microphone audio once connected."""
        await self.connected.wait()
        assert self.connection is not None, "Realtime connection was not established."

        read_size = int(SAMPLE_RATE * 0.02)
        stream = sd.InputStream(
            channels=CHANNELS, samplerate=SAMPLE_RATE, dtype="int16", device=self.input_device
        )
        stream.start()

        try:
            while True:
                if stream.read_available >= read_size:
                    data, _ = stream.read(read_size)
                    await self.connection.input_audio_buffer.append(
                        audio=base64.b64encode(cast(Any, data)).decode("utf-8")
                    )
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass
        finally:
            stream.stop()
            stream.close()