from pylsl import StreamInfo, StreamOutlet
import time

info = StreamInfo(name=‘annotations’,
                  type=‘Events’,
                  channel_count=1,
                  nominal_srate=0,
                  channel_format=‘float32’,
                  source_id='my_marker_stream')

outlet = StreamOutlet(info)

try:
    i = 1
    while True:
        marker = f"event_{i}"
        outlet.push_sample([1.0])
        print("Sent:", marker)
        i += 1
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopped.")
