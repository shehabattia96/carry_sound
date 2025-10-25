"""Audio sender application - captures system audio and streams it over UDP."""

import socket
import threading
import time
from typing import Optional

import click
import numpy as np
import sounddevice as sd


class AudioSender:
    """Captures audio from a device and streams it over UDP."""

    def __init__(
        self,
        target_host: str,
        target_port: int,
        device_id: Optional[int] = None,
        sample_rate: int = 44100,
        chunk_size: int = 1024,
        channels: int = 2,
    ):
        """Initialize the audio sender.

        Args:
            target_host: IP address of the receiver
            target_port: UDP port of the receiver
            device_id: Audio device ID (None for default)
            sample_rate: Sample rate in Hz
            chunk_size: Number of samples per chunk
            channels: Number of audio channels (1=mono, 2=stereo)
        """
        self.target_host = target_host
        self.target_port = target_port
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.is_running = False
        self.socket: Optional[socket.socket] = None
        self.stream: Optional[sd.InputStream] = None
        self.bytes_sent = 0
        self.chunks_sent = 0

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
        """Set up UDP socket for streaming."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        print(f"✓ Socket created and configured")

    def audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """Callback for audio stream - sends audio data over UDP.

        Args:
            indata: Audio data from the input device
            frames: Number of frames
            time_info: Time information
            status: Status information
        """
        if status:
            print(f"⚠ Audio callback status: {status}")

        try:
            # Convert audio data to bytes
            audio_bytes = indata.astype(np.float32).tobytes()

            # Send over UDP
            if self.socket:
                self.socket.sendto(audio_bytes, (self.target_host, self.target_port))
                self.bytes_sent += len(audio_bytes)
                self.chunks_sent += 1

        except Exception as e:
            print(f"✗ Error sending audio: {e}")

    def start(self) -> None:
        """Start capturing and streaming audio."""
        try:
            self.is_running = True
            self.setup_socket()

            print(f"Starting audio capture...")
            print(f"  Device: {self.device_id if self.device_id is not None else 'default'}")
            print(f"  Sample rate: {self.sample_rate} Hz")
            print(f"  Channels: {self.channels}")
            print(f"  Chunk size: {self.chunk_size}")
            print(f"  Target: {self.target_host}:{self.target_port}")
            print()

            # Create input stream
            self.stream = sd.InputStream(
                device=self.device_id,
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size,
                callback=self.audio_callback,
                latency="low",
            )

            self.stream.start()
            print("✓ Audio stream started")
            print("Streaming audio... (Press Ctrl+C to stop)")
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
        """Stop capturing and streaming audio."""
        self.is_running = False

        if self.stream:
            self.stream.stop()
            self.stream.close()
            print("✓ Audio stream stopped")

        if self.socket:
            self.socket.close()
            print("✓ Socket closed")

        # Print statistics
        if self.chunks_sent > 0:
            print(f"\nStatistics:")
            print(f"  Chunks sent: {self.chunks_sent}")
            print(f"  Bytes sent: {self.bytes_sent:,}")
            print(f"  Avg chunk size: {self.bytes_sent // self.chunks_sent} bytes")


@click.command()
@click.option(
    "--host",
    default="127.0.0.1",
    help="Target host IP address (default: 127.0.0.1)",
)
@click.option(
    "--port",
    default=5005,
    type=int,
    help="Target UDP port (default: 5005)",
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
    "--chunk-size",
    default=1024,
    type=int,
    help="Chunk size in samples (default: 1024)",
)
@click.option(
    "--channels",
    default=2,
    type=int,
    help="Number of channels: 1=mono, 2=stereo (default: 2)",
)
@click.option(
    "--list-devices",
    is_flag=True,
    help="List available audio devices and exit",
)
def main(host: str, port: int, device: Optional[int], sample_rate: int, chunk_size: int, channels: int, list_devices: bool) -> None:
    """Capture system audio and stream it over UDP."""
    sender = AudioSender(
        target_host=host,
        target_port=port,
        device_id=device,
        sample_rate=sample_rate,
        chunk_size=chunk_size,
        channels=channels,
    )

    if list_devices:
        sender.list_devices()
    else:
        sender.start()


if __name__ == "__main__":
    main()

