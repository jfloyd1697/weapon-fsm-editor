from pathlib import Path
import struct

from weapon_fsm_workspace.hardware_bridge.client import (
    BridgeOp, FrameParser, encode_frame, crc16, BridgeClient, BridgeMode, ProtocolError,
)


def test_crc16_reference():
    assert crc16(b"123456789") == 0x29B1


def test_frame_roundtrip():
    parser = FrameParser()
    command = encode_frame(BridgeOp.INPUT, 0x1234, b"\x03\x01")
    assert parser.feed(command[:4]) == []
    assert parser.feed(command[4:7]) == []
    results = parser.feed(command[7:])
    assert len(results) == 1
    assert results[0].op == BridgeOp.INPUT
    assert results[0].sequence == 0x1234
    assert results[0].payload == b"\x03\x01"


def test_resync_corrupt_and_console_output():
    parser = FrameParser()
    good = encode_frame(BridgeOp.ACK, 33, b"\x00")
    bad = bytearray(good)
    bad[-1] ^= 1
    assert parser.feed(b"[LOG] hello\n" + bytes(bad) + good)[0].sequence == 33


def test_payload_limit():
    try:
        encode_frame(BridgeOp.FILE_CHUNK, 1, b"x" * 513)
    except ValueError:
        pass
    else:
        assert False


def test_mode_and_deploy_require_connection(tmp_path):
    client = BridgeClient()
    try:
        client.set_mode(BridgeMode.REMOTE_INPUT)
    except ProtocolError:
        pass
    else:
        assert False
    asset = tmp_path / "x.bin"
    asset.write_bytes(b"abc")
    try:
        client.deploy_file(asset, "assets/x.bin")
    except ProtocolError:
        pass
    else:
        assert False
