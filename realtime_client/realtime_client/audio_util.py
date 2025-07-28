import base64
import asyncio
import threading
from typing import Callable, Awaitable

import numpy as np
import sounddevice as sd

from openai.resources.beta.realtime.realtime import AsyncRealtimeConnection

CHUNK_LENGTH_S = 0.05
SAMPLE_RATE = 24000
FORMAT = None
CHANNELS = 1

def audio_to_pcm16_base64(audio_bytes: bytes) -> bytes:
    """Converts audio bytes to 24kHz mono PCM16 and returns as bytes."""
    # unused atm.
    return audio_bytes # Simplified, as pydub is removed


class AudioPlayerAsync:
    """Asynchronously plays audio data."""
    def __init__(self, device: int | None = None):
        self.queue = []
        self.lock = threading.Lock()
        self.stream = sd.OutputStream(
            callback=self.callback,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=np.int16,
            blocksize=int(CHUNK_LENGTH_S * SAMPLE_RATE),
            device=device,
        )
        self.playing = False
        self._frame_count = 0

    def callback(self, outdata, frames, time, status):  # noqa
        """Callback function for the audio stream."""
        with self.lock:
            data = np.empty(0, dtype=np.int16)

            while len(data) < frames and len(self.queue) > 0:
                item = self.queue.pop(0)
                frames_needed = frames - len(data)
                data = np.concatenate((data, item[:frames_needed]))
                if len(item) > frames_needed:
                    self.queue.insert(0, item[frames_needed:])

            self._frame_count += len(data)

            if len(data) < frames:
                data = np.concatenate((data, np.zeros(frames - len(data), dtype=np.int16)))

        outdata[:] = data.reshape(-1, 1)

    def reset_frame_count(self):
        """Resets the audio frame count."""
        self._frame_count = 0

    def get_frame_count(self):
        """Returns the current audio frame count."""
        return self._frame_count

    def add_data(self, data: bytes):
        """Adds audio data to the playback queue."""
        with self.lock:
            np_data = np.frombuffer(data, dtype=np.int16)
            self.queue.append(np_data)
            if not self.playing:
                self.start()

    def start(self):
        """Starts the audio playback stream."""
        self.playing = True
        self.stream.start()

    def stop(self):
        """Stops the audio playback stream."""
        self.playing = False
        self.stream.stop()
        with self.lock:
            self.queue = []

    def terminate(self):
        """Terminates the audio stream."""
        self.stream.close()


async def send_audio_worker_sounddevice(
    connection: AsyncRealtimeConnection,
    should_send: Callable[[], bool] | None = None,
    start_send: Callable[[], Awaitable[None]] | None = None,
):
    """Sends audio data from the microphone to the connection."""
    sent_audio = False

    read_size = int(SAMPLE_RATE * 0.02)

    stream = sd.InputStream(
        channels=CHANNELS,
        samplerate=SAMPLE_RATE,
        dtype="int16",
    )
    stream.start()

    try:
        while True:
            if stream.read_available < read_size:
                await asyncio.sleep(0)
                continue

            data, _ = stream.read(read_size)

            if should_send() if should_send else True:
                if not sent_audio and start_send:
                    await start_send()
                await connection.send(
                    {"type": "input_audio_buffer.append", "audio": base64.b64encode(data).decode("utf-8")}
                )
                sent_audio = True

            elif sent_audio:
                await connection.send({"type": "input_audio_buffer.commit"})
                await connection.send({"type": "response.create", "response": {}})
                sent_audio = False

            await asyncio.sleep(0)

    except KeyboardInterrupt:
        pass
    finally:
        stream.stop()
        stream.close()