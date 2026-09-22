import pyaudio
import audioop

p = pyaudio.PyAudio()

test_indices = [1, 2, 6, 8, 14, 15]

for idx in test_indices:
    try:
        info = p.get_device_info_by_index(idx)
        channels = int(min(info.get('maxInputChannels', 1), 2))
        rate = int(info.get('defaultSampleRate', 44100))
        stream = p.open(format=pyaudio.paInt16, channels=channels, rate=rate, input=True, input_device_index=idx, frames_per_buffer=1024)
        total_rms = 0
        samples = 0
        for _ in range(10): # ~250ms
            data = stream.read(1024, exception_on_overflow=False)
            rms = audioop.rms(data, 2)
            total_rms += rms
            samples += 1
        stream.stop_stream()
        stream.close()
        avg_rms = total_rms / samples
        print(f"Device [{idx}] {info['name']} (Rate={rate}, Ch={channels}) -> Avg RMS = {avg_rms:.2f}")
    except Exception as e:
        print(f"Device [{idx}] failed: {e}")

p.terminate()
