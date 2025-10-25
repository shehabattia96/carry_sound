"""Audio receiver application - receives audio stream over UDP and plays it."""

import socket
import threading
import time
from collections import deque
from typing import Optional

import click
import numpy as np
import sounddevice as sd


class AudioReceiver:
    """Receives audio stream over UDP and plays it."""

    def __init__(
        self,
        listen_port: int,
        device_id: Optional[int] = None,
        sample_rate: int = 44100,
        channels: int = 2,
        buffer_size: int = 10,
        chunk_size: int = 1024,
    ):
        """Initialize the audio receiver.

        Args:
            listen_port: UDP port to listen on
            device_id: Audio device ID (None for default)
            sample_rate: Sample rate in Hz
            channels: Number of audio channels (1=mono, 2=stereo)
            buffer_size: Number of chunks to buffer before playing
            chunk_size: Number of samples per chunk (must match sender)
        """
        self.listen_port = listen_port
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer_size = buffer_size
        self.chunk_size = chunk_size
        self.is_running = False
        self.socket: Optional[socket.socket] = None
        self.stream: Optional[sd.OutputStream] = None
        self.audio_buffer: deque = deque(maxlen=buffer_size)
        self.receive_thread: Optional[threading.Thread] = None
        self.bytes_received = 0
        self.chunks_received = 0
        self.underruns = 0
        self.partial_chunk: Optional[np.ndarray] = None

    def list_devices(self) -> None:
        """List all available audio devices."""
        devices = sd.query_devices()
        print("\nAvailable audio devices:")
        print("-" * 80)
        for i, device in enumerate(devices):
            print(f"[{i}] {device['name']}")
            print(f"    Channels: {device['max_input_channels']} in, {device['max_output_channels']} out")
            print(f"    Sample rate: {device['default_samplerate']} Hz")
            print()

    def setup_socket(self) -> None:
        """Set up UDP socket for receiving."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        self.socket.bind(("0.0.0.0", self.listen_port))
        self.socket.settimeout(1.0)
        print(f"✓ Socket created and listening on port {self.listen_port}")

    def receive_audio(self) -> None:
        """Receive audio data from UDP socket."""
        print("✓ Receive thread started")
        while self.is_running:
            try:
                data, addr = self.socket.recvfrom(65536)
                self.bytes_received += len(data)
                self.chunks_received += 1

                # Convert bytes to audio data
                audio_data = np.frombuffer(data, dtype=np.float32)
                audio_data = audio_data.reshape(-1, self.channels)

                # Add to buffer
                self.audio_buffer.append(audio_data)

            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"⚠ Error receiving audio: {e}")

    def audio_callback(self, outdata: np.ndarray, frames: int, time_info, status) -> None:
        """Callback for audio stream - plays audio from buffer.

        Args:
            outdata: Audio buffer to fill
            frames: Number of frames requested
            time_info: Time information
            status: Status information
        """
        if status:
            print(f"⚠ Audio callback status: {status}")

        try:
            frames_written = 0

            # First, use any partial chunk from previous callback
            if self.partial_chunk is not None and len(self.partial_chunk) > 0:
                frames_to_copy = min(len(self.partial_chunk), frames - frames_written)
                outdata[frames_written:frames_written + frames_to_copy] = self.partial_chunk[:frames_to_copy]
                frames_written += frames_to_copy

                # Keep remaining data for next callback
                if frames_to_copy < len(self.partial_chunk):
                    self.partial_chunk = self.partial_chunk[frames_to_copy:]
                else:
                    self.partial_chunk = None

            # Fill remaining frames from buffer
            while frames_written < frames and self.audio_buffer:
                audio_chunk = self.audio_buffer.popleft()
                frames_to_copy = min(len(audio_chunk), frames - frames_written)
                outdata[frames_written:frames_written + frames_to_copy] = audio_chunk[:frames_to_copy]
                frames_written += frames_to_copy

                # Save any leftover data for next callback
                if frames_to_copy < len(audio_chunk):
                    self.partial_chunk = audio_chunk[frames_to_copy:]

            # Fill any remaining frames with silence
            if frames_written < frames:
                outdata[frames_written:].fill(0)
                if frames_written == 0:  # Only count as underrun if we had no data at all
                    self.underruns += 1

        except Exception as e:
            print(f"✗ Error in audio callback: {e}")
            outdata.fill(0)

    def start(self) -> None:
        """Start receiving and playing audio."""
        try:
            self.is_running = True
            self.setup_socket()

            print(f"Starting audio receiver...")
            print(f"  Listen port: {self.listen_port}")
            print(f"  Device: {self.device_id if self.device_id is not None else 'default'}")
            print(f"  Sample rate: {self.sample_rate} Hz")
            print(f"  Channels: {self.channels}")
            print(f"  Chunk size: {self.chunk_size}")
            print(f"  Buffer size: {self.buffer_size} chunks")
            print()

            # Start receive thread
            self.receive_thread = threading.Thread(target=self.receive_audio, daemon=True)
            self.receive_thread.start()

            # Create output stream with matching blocksize
            self.stream = sd.OutputStream(
                device=self.device_id,
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size,
                callback=self.audio_callback,
                latency="low",
            )

            self.stream.start()
            print("✓ Audio stream started")
            print("Waiting for audio... (Press Ctrl+C to stop)")
            print()

            # Keep the stream running
            try:
                while self.is_running:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n\nStopping...")

        except Exception as e:
            print(f"✗ Error: {e}")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop receiving and playing audio."""
        self.is_running = False

        if self.stream:
            self.stream.stop()
            self.stream.close()
            print("✓ Audio stream stopped")

        if self.socket:
            self.socket.close()
            print("✓ Socket closed")

        # Print statistics
        if self.chunks_received > 0:
            print(f"\nStatistics:")
            print(f"  Chunks received: {self.chunks_received}")
            print(f"  Bytes received: {self.bytes_received:,}")
            print(f"  Avg chunk size: {self.bytes_received // self.chunks_received} bytes")
            print(f"  Buffer underruns: {self.underruns}")


@click.command()
@click.option(
    "--port",
    default=5005,
    type=int,
    help="UDP port to listen on (default: 5005)",
)
@click.option(
    "--device",
    default=None,
    type=int,
    help="Audio device ID (use --list-devices to see available devices)",
)
@click.option(
    "--sample-rate",
    default=44100,
    type=int,
    help="Sample rate in Hz (default: 44100)",
)
@click.option(
    "--channels",
    default=2,
    type=int,
    help="Number of channels: 1=mono, 2=stereo (default: 2)",
)
@click.option(
    "--chunk-size",
    default=1024,
    type=int,
    help="Chunk size in samples (must match sender, default: 1024)",
)
@click.option(
    "--buffer-size",
    default=10,
    type=int,
    help="Buffer size in chunks (default: 10)",
)
@click.option(
    "--list-devices",
    is_flag=True,
    help="List available audio devices and exit",
)
def main(port: int, device: Optional[int], sample_rate: int, channels: int, chunk_size: int, buffer_size: int, list_devices: bool) -> None:
    """Receive audio stream over UDP and play it."""
    receiver = AudioReceiver(
        listen_port=port,
        device_id=device,
        sample_rate=sample_rate,
        channels=channels,
        chunk_size=chunk_size,
        buffer_size=buffer_size,
    )

    if list_devices:
        receiver.list_devices()
    else:
        receiver.start()


if __name__ == "__main__":
    main()

