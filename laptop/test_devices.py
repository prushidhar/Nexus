import pyaudio

p = pyaudio.PyAudio()
count = p.get_device_count()
print(f"Total devices: {count}")
for i in range(count):
    info = p.get_device_info_by_index(i)
    if info.get('maxInputChannels', 0) > 0:
        print(f"Index [{i}]: {info.get('name')} | HostApi={info.get('hostApi')} | Channels={info.get('maxInputChannels')} | Rate={info.get('defaultSampleRate')}")

default_input = p.get_default_input_device_info()
print(f"DEFAULT INPUT: [{default_input['index']}] {default_input['name']}")
p.terminate()
