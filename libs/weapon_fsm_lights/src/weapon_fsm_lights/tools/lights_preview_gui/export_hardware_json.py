from weapon_fsm_lights import load_canvas_animation_sequence, export_hardware_sequence_json

asset = load_canvas_animation_sequence("../../../../examples/charge_glow.canvas.yaml")
export_hardware_sequence_json(asset, "charge_glow.hardware.json")