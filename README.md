# Carry Sound - Low-Latency Audio Streaming

A Python-based application for capturing system audio on one computer and streaming it over a local network to another computer with minimal latency.

## Features

- **Low-latency streaming**: Target latency <100ms on local networks
- **Cross-platform audio support**: Works on macOS, Windows, and Linux
- **UDP-based streaming**: Optimized for speed over reliability on local networks
- **Configurable audio parameters**: Sample rate, channels, chunk size
- **Device selection**: Choose specific audio input/output devices
- **Buffer management**: Adjustable buffering to balance latency and stability
- **Statistics tracking**: Monitor bytes sent/received and buffer underruns

## System Requirements

### Prerequisites

- **Python**: 3.9 or higher
- **uv**: Python package manager (install from https://astral.sh/uv)
- **Network**: Both computers on the same local network (LAN)
- **Audio drivers**: Working audio input/output drivers

### OS-Specific Requirements

#### macOS
- **Audio Capture Permission**: First run will prompt for microphone access
  - Go to System Preferences → Security & Privacy → Microphone
  - Grant permission to Terminal or your Python IDE
- **Loopback Audio**: To capture system audio (not just microphone):
  - Install **BlackHole** (free): https://github.com/ExistentialAudio/BlackHole
  - Or use **SoundFlower** (legacy): https://github.com/mattingalls/Soundflower
  - Set the loopback device as the input device in the sender

#### Windows
- **Audio Drivers**: Ensure audio drivers are up to date
- **Firewall**: May need to allow Python through Windows Defender Firewall
- **WASAPI**: Uses Windows Audio Session API for audio capture
- **System Audio Capture**: Use VB-Audio Virtual Cable or similar for system audio:
  - Download from https://vb-audio.com/Cable/
  - Set as default playback device, then select as input in sender

#### Linux
- **ALSA/PulseAudio**: Ensure audio system is properly configured
- **Permissions**: User must be in `audio` group: `sudo usermod -aG audio $USER`
- **System Audio**: Use PulseAudio loopback module or JACK for system audio capture

## Installation

### 1. Install uv (if not already installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone or download the project

```bash
cd /path/to/carry_sound
```

### 3. Install dependencies using uv

```bash
uv sync
```

This will:
- Create a virtual environment
- Install all dependencies from `pyproject.toml`
- Set up the project for development

### 4. Verify installation

```bash
# List available audio devices
uv run carry_sound --list-devices
uv run carry_sound_receive --list-devices
```

## Configuration

### Finding Your Audio Devices

Before running the application, identify your audio devices:

```bash
# On sender computer
uv run carry_sound --list-devices

# On receiver computer
uv run carry_sound_receive --list-devices
```

Output example:
```
Available audio devices:
[0] Built-in Microphone
    Channels: 1 in, 0 out
    Sample rate: 48000 Hz

[1] BlackHole 2ch
    Channels: 2 in, 0 out
    Sample rate: 48000 Hz

[2] Built-in Speaker
    Channels: 0 in, 2 out
    Sample rate: 48000 Hz
```

### Network Configuration

1. **Find your IP address**:
   - **macOS/Linux**: `ifconfig | grep "inet "`
   - **Windows**: `ipconfig`

2. **Ensure both computers are on the same subnet** (e.g., 192.168.1.x)

3. **Check firewall settings**:
   - Ensure UDP port 5005 (or your chosen port) is not blocked
   - May need to add Python to firewall exceptions

## Usage

### Basic Setup (Same Computer - Testing)

Perfect for testing on a single machine:

**Terminal 1 - Receiver:**
```bash
uv run carry_sound_receive --port 5005
```

**Terminal 2 - Sender:**
```bash
uv run carry_sound --host 127.0.0.1 --port 5005 --device 0
```

### Network Setup (Two Computers)

**On Receiver Computer:**
```bash
# Find your IP address
ifconfig | grep "inet "

# Start receiver (listens on all interfaces)
uv run carry_sound_receive --port 5005
```

**On Sender Computer:**
```bash
# Replace 192.168.1.100 with receiver's IP address
uv run carry_sound --host 192.168.1.100 --port 5005 --device 1
```

### Advanced Options

#### Sender Options
```bash
uv run carry_sound --help

Options:
  --host TEXT              Target host IP address (default: 127.0.0.1)
  --port INTEGER           Target UDP port (default: 5005)
  --device INTEGER         Audio device ID (use --list-devices to see available)
  --sample-rate INTEGER    Sample rate in Hz (default: 44100)
  --chunk-size INTEGER     Chunk size in samples (default: 1024)
  --channels INTEGER       Number of channels: 1=mono, 2=stereo (default: 2)
  --list-devices           List available audio devices and exit
```

#### Receiver Options
```bash
uv run carry_sound_receive --help

Options:
  --port INTEGER           UDP port to listen on (default: 5005)
  --device INTEGER         Audio device ID (use --list-devices to see available)
  --sample-rate INTEGER    Sample rate in Hz (default: 44100)
  --channels INTEGER       Number of channels: 1=mono, 2=stereo (default: 2)
  --buffer-size INTEGER    Buffer size in chunks (default: 10)
  --list-devices           List available audio devices and exit
```

### Configuration Examples

#### Low Latency (Mono, 16kHz)
```bash
# Sender
uv run carry_sound --host 192.168.1.100 --sample-rate 16000 --channels 1 --chunk-size 512

# Receiver
uv run carry_sound_receive --sample-rate 16000 --channels 1 --buffer-size 5
```

#### High Quality (Stereo, 48kHz)
```bash
# Sender
uv run carry_sound --host 192.168.1.100 --sample-rate 48000 --channels 2 --chunk-size 2048

# Receiver
uv run carry_sound_receive --sample-rate 48000 --channels 2 --buffer-size 15
```

#### Custom Port
```bash
# Sender
uv run carry_sound --host 192.168.1.100 --port 9999

# Receiver
uv run carry_sound_receive --port 9999
```

## Latency Analysis

### Expected Latency Breakdown

| Component | Latency |
|-----------|---------|
| Audio capture buffer | 10-50ms |
| Network transmission | 1-10ms (LAN) |
| Receiver buffer | 10-100ms |
| Audio playback buffer | 10-50ms |
| **Total** | **31-210ms** |

### Optimizing for Low Latency

1. **Reduce chunk size**: Smaller chunks = lower latency but higher CPU usage
   - Default: 1024 samples (~23ms at 44.1kHz)
   - Low latency: 512 samples (~12ms at 44.1kHz)

2. **Reduce buffer size**: Fewer buffered chunks = lower latency but more underruns
   - Default: 10 chunks
   - Low latency: 3-5 chunks (may cause audio dropouts on unstable networks)

3. **Lower sample rate**: Reduces data size and processing time
   - 44.1kHz: Standard quality
   - 16kHz: Lower quality but faster

4. **Use mono instead of stereo**: Reduces data by 50%

5. **Ensure network stability**: Use wired Ethernet instead of WiFi

### Measuring Latency

1. **Visual method**: Play a video on sender, measure delay on receiver
2. **Audio method**: Use a tone generator and measure phase difference
3. **Network method**: Monitor UDP packet timestamps

## Troubleshooting

### No Audio Received

**Problem**: Receiver starts but no audio is heard

**Solutions**:
1. Verify sender is running: Check for "Streaming audio..." message
2. Check IP address: Ensure `--host` matches receiver's IP
3. Check port: Ensure both use same port (default: 5005)
4. Check firewall: Allow UDP port 5005
5. Check device: Verify correct device ID with `--list-devices`
6. Test locally first: Use `--host 127.0.0.1` on same computer

### Audio Dropouts / Underruns

**Problem**: Audio cuts out or has gaps

**Solutions**:
1. Increase buffer size: `--buffer-size 15` (receiver)
2. Increase chunk size: `--chunk-size 2048` (sender)
3. Check network: Use wired connection instead of WiFi
4. Reduce sample rate: Use 44100 instead of 48000
5. Close other applications: Reduce CPU load
6. Check network congestion: Run `ping` to receiver to check latency

### High Latency

**Problem**: Audio is delayed significantly

**Solutions**:
1. Reduce buffer size: `--buffer-size 5` (receiver)
2. Reduce chunk size: `--chunk-size 512` (sender)
3. Use lower sample rate: `--sample-rate 16000`
4. Use mono: `--channels 1`
5. Check network: Ensure low ping time (<10ms)

### Device Not Found

**Problem**: "Device not found" error

**Solutions**:
1. List devices: `uv run carry_sound --list-devices`
2. Use correct device ID: Device IDs are shown in brackets [0], [1], etc.
3. Restart audio system: May need to restart audio drivers
4. Check permissions: Ensure user has audio device access

### Permission Denied (macOS)

**Problem**: "Permission denied" when accessing microphone

**Solutions**:
1. Grant microphone permission:
   - System Preferences → Security & Privacy → Microphone
   - Add Terminal or Python IDE to allowed apps
2. Restart Terminal/IDE after granting permission
3. For system audio: Install BlackHole or SoundFlower

### Connection Refused

**Problem**: "Connection refused" or "Network unreachable"

**Solutions**:
1. Verify receiver is running
2. Check IP address is correct
3. Verify both computers are on same network
4. Check firewall settings
5. Try ping: `ping 192.168.1.100` (replace with receiver IP)

### High CPU Usage

**Problem**: Application uses excessive CPU

**Solutions**:
1. Increase chunk size: `--chunk-size 2048`
2. Increase buffer size: `--buffer-size 15`
3. Lower sample rate: `--sample-rate 22050`
4. Close other applications
5. Check for CPU throttling

## Performance Characteristics

### Bandwidth Usage

- **44.1kHz, 16-bit, Stereo**: ~172 KB/s
- **44.1kHz, 16-bit, Mono**: ~86 KB/s
- **16kHz, 16-bit, Mono**: ~32 KB/s

### CPU Usage

- **Typical**: 2-5% per application
- **High quality (48kHz, stereo)**: 5-10%
- **Low latency (512 chunk size)**: 8-15%

### Network Requirements

- **Minimum bandwidth**: 100 KB/s (for 44.1kHz stereo)
- **Recommended**: 1 Mbps+ for stable streaming
- **Optimal**: Wired Ethernet with <10ms latency

## Development

### Running Tests

```bash
uv run pytest
```

### Code Quality

```bash
# Format code
uv run black carry_sound/

# Lint code
uv run ruff check carry_sound/

# Type checking
uv run mypy carry_sound/
```

## Limitations

- **UDP-based**: Packets may be lost on unstable networks (use TCP for reliability)
- **No encryption**: Audio is sent unencrypted over the network
- **No authentication**: No user authentication or access control
- **Single stream**: Only one sender-receiver pair per port
- **Latency**: Cannot achieve <30ms on typical networks due to OS buffering

## Future Enhancements

- [ ] TCP mode for reliable streaming
- [ ] Audio compression (opus, AAC)
- [ ] Encryption support
- [ ] Multiple concurrent streams
- [ ] Web UI for configuration
- [ ] Automatic device detection
- [ ] Audio level monitoring
- [ ] Recording to file

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions, please open an issue on the project repository.

