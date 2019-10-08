import asyncio as aio
from ndn.encoding import parse_tl_num
from ndn.transport.stream_socket import Face


class DummyFace(Face):
    app = None

    def __init__(self, test_func):
        super().__init__()
        self.output_buf = b''
        self.test_func = test_func
        self.event = aio.Event()
        self.expected_len = 2 ** 32

    async def open(self):
        self.running = True

    def shutdown(self):
        self.running = False

    def send(self, data: bytes):
        self.output_buf += data
        if len(self.output_buf) >= self.expected_len:
            self.event.set()

    async def run(self):
        await self.test_func(self)
        if self.app:
            self.app.shutdown()

    async def consume_output(self, expected_output, timeout=0.01):
        self.expected_len = len(expected_output)
        if len(self.output_buf) < self.expected_len:
            await aio.wait_for(self.event.wait(), timeout)
        self.expected_len = 2 ** 32
        self.event.clear()
        assert self.output_buf == expected_output
        self.output_buf = b''

    async def ignore_output(self, length, timeout=0.1):
        self.expected_len = length
        await aio.wait_for(self.event.wait(), timeout)
        self.expected_len = 2 ** 32
        self.event.clear()
        self.output_buf = b''

    async def input_packet(self, packet):
        packet = memoryview(packet)
        typ, typ_len = parse_tl_num(packet)
        siz, siz_len = parse_tl_num(packet, typ_len)
        offset = typ_len + siz_len
        assert len(packet) == offset + siz
        await self.callback(typ, packet[offset:])
