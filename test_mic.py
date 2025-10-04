import sounddevice as sd
import numpy as np

# List all audio devices
print("Available audio devices:")
print(sd.query_devices())

# Test default microphone
print("\nTesting default microphone...")
duration = 5  # seconds
fs = 44100  # sample rate

try:
    print("Recording for 5 seconds...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()  # Wait until recording is finished
    print("Recording complete!")
    
    # Check if audio was captured
    if np.max(np.abs(recording)) > 0.01:  # Threshold for silence
        print("Microphone is working properly!")
    else:
        print("Warning: No significant audio detected")
        
except Exception as e:
    print(f"Error: {e}")
    print("Microphone test failed")