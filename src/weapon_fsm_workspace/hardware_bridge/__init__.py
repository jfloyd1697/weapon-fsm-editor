"""USB CDC bridge between Weapon FSM Editor and a blaster firmware target."""
from .client import BridgeClient, BridgeMode, BridgeOp, ProtocolError, encode_frame, FrameParser

__all__ = ["BridgeClient", "BridgeMode", "BridgeOp", "ProtocolError", "encode_frame", "FrameParser"]
