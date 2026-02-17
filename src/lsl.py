from pylsl import StreamInfo, StreamOutlet


class LSLOutlet:
    def __init__(self, logger):
        info = StreamInfo(
            name="annotations",
            type="Events",
            channel_count=1,
            nominal_srate=0,
            channel_format="string",
            source_id="my_marker_stream",
        )
        self.outlet = StreamOutlet(info)
        self.logger = logger

    def send(self, message: str):
        self.outlet.push_sample([message])
        if self.logger:
            self.logger.write(message)
