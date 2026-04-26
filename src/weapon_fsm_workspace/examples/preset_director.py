from pathlib import Path

import yaml


class DemoPresetDirector:
    def build_common_gun(self) -> dict:
        return {
            "gun": {
                "events": [
                    {"id": "on_equip"},
                    {"id": "trigger_pressed"},
                    {"id": "trigger_released"},
                    {"id": "reload_pressed"},
                    {"id": "fire_tick"},
                    {"id": "charge_tick"},
                    {"id": "shot_done"},
                    {"id": "reload_complete"},
                ]
            }
        }

    def build_full_auto_with_ammo(self) -> tuple[dict, dict]:
        gun = self.build_common_gun()
        weapon = {
            "weapon": {
                "initial_state": "ready",
                "variables": {
                    "ammo": 30,
                    "mag_capacity": 30,
                },
                "states": [
                    {"id": "ready", "label": "Ready"},
                    {
                        "id": "firing",
                        "label": "Firing",
                        "on_entry": [
                            {"type": "play_audio", "clip": "auto_shot", "interrupt": "interrupt"},
                            {"type": "start_light_sequence", "sequence": "muzzle_flash"},
                            {"type": "adjust_ammo", "delta": -1},
                            {"type": "schedule_event", "event": "fire_tick", "delay_ms": 65},
                        ],
                    },
                    {
                        "id": "reloading",
                        "label": "Reloading",
                        "on_entry": [
                            {"type": "stop_audio"},
                            {"type": "stop_light_sequence"},
                            {"type": "play_audio", "clip": "reload", "interrupt": "interrupt"},
                            {"type": "start_light_sequence", "sequence": "reload"},
                            {"type": "schedule_event", "event": "reload_complete", "delay_ms": 1200},
                        ],
                    },
                    {"id": "empty", "label": "Empty"},
                ],
                "transitions": [
                    {
                        "id": "start_firing",
                        "source": "ready",
                        "trigger": "trigger_pressed",
                        "target": "firing",
                        "guard": {"var_gt": {"name": "ammo", "value": 0}},
                    },
                    {
                        "id": "pull_on_empty",
                        "source": "ready",
                        "trigger": "trigger_pressed",
                        "target": "empty",
                        "guard": {"var_lte": {"name": "ammo", "value": 0}},
                    },
                    {
                        "id": "continue_firing",
                        "source": "firing",
                        "trigger": "fire_tick",
                        "target": "firing",
                        "guard": {
                            "all": [
                                {"trigger_pressed": True},
                                {"var_gt": {"name": "ammo", "value": 0}},
                            ]
                        },
                    },
                    {
                        "id": "release_to_ready",
                        "source": "firing",
                        "trigger": "trigger_released",
                        "target": "ready",
                    },
                    {
                        "id": "tick_to_empty",
                        "source": "firing",
                        "trigger": "fire_tick",
                        "target": "empty",
                        "guard": {"var_lte": {"name": "ammo", "value": 0}},
                    },
                    {
                        "id": "reload_from_ready",
                        "source": "ready",
                        "trigger": "reload_pressed",
                        "target": "reloading",
                    },
                    {
                        "id": "reload_from_empty",
                        "source": "empty",
                        "trigger": "reload_pressed",
                        "target": "reloading",
                    },
                    {
                        "id": "reload_done",
                        "source": "reloading",
                        "trigger": "reload_complete",
                        "target": "ready",
                        "actions": [
                            {"type": "set_ammo_full"},
                        ],
                    },
                ],
            },
            "clips": {
                "auto_shot": {"path": "assets/audio/full_auto/shot.wav"},
                "reload": {"path": "assets/audio/shared/reload.wav"},
            },
            "light_sequences": {
                "muzzle_flash": {"path": "assets/lights/muzzle_flash.yaml"},
                "reload": {"path": "assets/lights/reload.yaml"},
            },
        }
        return gun, weapon

    def build_charge_shot(self) -> tuple[dict, dict]:
        gun = self.build_common_gun()
        weapon = {
            "weapon": {
                "initial_state": "ready",
                "variables": {
                    "ammo": 6,
                    "mag_capacity": 6,
                    "charge_ticks": 0,
                    "charge_threshold": 25,
                },
                "states": [
                    {"id": "ready", "label": "Ready"},
                    {
                        "id": "charging",
                        "label": "Charging",
                        "on_entry": [
                            {"type": "play_audio_loop", "clip": "charge_loop", "interrupt": "ignore"},
                            {"type": "start_light_sequence", "sequence": "charge_glow"},
                            {"type": "schedule_event", "event": "charge_tick", "delay_ms": 10},
                        ],
                    },
                    {
                        "id": "charged",
                        "label": "Charged",
                        "on_entry": [
                            {"type": "stop_audio"},
                            {"type": "play_audio", "clip": "charged_ready", "interrupt": "interrupt"},
                            {"type": "start_light_sequence", "sequence": "charged_glow"},
                        ],
                    },
                    {
                        "id": "firing",
                        "label": "Firing",
                        "on_entry": [
                            {"type": "stop_audio"},
                            {"type": "stop_light_sequence"},
                            {"type": "play_audio", "clip": "charged_fire", "interrupt": "interrupt"},
                            {"type": "start_light_sequence", "sequence": "big_flash"},
                            {"type": "adjust_ammo", "delta": -1},
                            {"type": "set_var", "name": "charge_ticks", "value": 0},
                            {"type": "schedule_event", "event": "shot_done", "delay_ms": 180},
                        ],
                    },
                    {
                        "id": "reloading",
                        "label": "Reloading",
                        "on_entry": [
                            {"type": "stop_audio"},
                            {"type": "stop_light_sequence"},
                            {"type": "set_var", "name": "charge_ticks", "value": 0},
                            {"type": "play_audio", "clip": "reload", "interrupt": "interrupt"},
                            {"type": "start_light_sequence", "sequence": "reload"},
                            {"type": "schedule_event", "event": "reload_complete", "delay_ms": 1200},
                        ],
                    },
                    {"id": "empty", "label": "Empty"},
                ],
                "transitions": [
                    {
                        "id": "start_charge",
                        "source": "ready",
                        "trigger": "trigger_pressed",
                        "target": "charging",
                        "guard": {"var_gt": {"name": "ammo", "value": 0}},
                        "actions": [
                            {"type": "set_var", "name": "charge_ticks", "value": 0},
                        ],
                    },
                    {
                        "id": "pull_on_empty",
                        "source": "ready",
                        "trigger": "trigger_pressed",
                        "target": "empty",
                        "guard": {"var_lte": {"name": "ammo", "value": 0}},
                    },
                    {
                        "id": "charge_tick_continue",
                        "source": "charging",
                        "trigger": "charge_tick",
                        "target": "charging",
                        "guard": {
                            "all": [
                                {"trigger_pressed": True},
                                {"var_lt": {"name": "charge_ticks", "value_from_var": "charge_threshold"}},
                            ]
                        },
                        "actions": [
                            {"type": "add_var", "name": "charge_ticks", "value": 1},
                            {"type": "schedule_event", "event": "charge_tick", "delay_ms": 10},
                        ],
                    },
                    {
                        "id": "charge_done",
                        "source": "charging",
                        "trigger": "charge_tick",
                        "target": "charged",
                        "guard": {
                            "all": [
                                {"trigger_pressed": True},
                                {"var_gte": {"name": "charge_ticks", "value_from_var": "charge_threshold"}},
                            ]
                        },
                    },
                    {
                        "id": "release_early",
                        "source": "charging",
                        "trigger": "trigger_released",
                        "target": "ready",
                        "guard": {"var_lt": {"name": "charge_ticks", "value_from_var": "charge_threshold"}},
                        "actions": [
                            {"type": "stop_audio"},
                            {"type": "stop_light_sequence"},
                            {"type": "play_audio", "clip": "charge_fail", "interrupt": "interrupt"},
                            {"type": "set_var", "name": "charge_ticks", "value": 0},
                        ],
                    },
                    {
                        "id": "release_charged",
                        "source": "charged",
                        "trigger": "trigger_released",
                        "target": "firing",
                    },
                    {
                        "id": "shot_done_ready",
                        "source": "firing",
                        "trigger": "shot_done",
                        "target": "ready",
                        "guard": {"var_gt": {"name": "ammo", "value": 0}},
                    },
                    {
                        "id": "shot_done_empty",
                        "source": "firing",
                        "trigger": "shot_done",
                        "target": "empty",
                        "guard": {"var_lte": {"name": "ammo", "value": 0}},
                    },
                    {
                        "id": "reload_from_ready",
                        "source": "ready",
                        "trigger": "reload_pressed",
                        "target": "reloading",
                    },
                    {
                        "id": "reload_from_empty",
                        "source": "empty",
                        "trigger": "reload_pressed",
                        "target": "reloading",
                    },
                    {
                        "id": "reload_done",
                        "source": "reloading",
                        "trigger": "reload_complete",
                        "target": "ready",
                        "actions": [
                            {"type": "set_ammo_full"},
                        ],
                    },
                ],
            },
            "clips": {
                "charge_loop": {"path": "assets/audio/charge/charge_loop.wav"},
                "charged_ready": {"path": "assets/audio/charge/charged_ready.wav"},
                "charge_fail": {"path": "assets/audio/charge/charge_fail.wav"},
                "charged_fire": {"path": "assets/audio/charge/charged_fire.wav"},
                "reload": {"path": "assets/audio/shared/reload.wav"},
            },
            "light_sequences": {
                "charge_glow": {"path": "assets/lights/charge_glow.yaml"},
                "charged_glow": {"path": "assets/lights/charged_glow.yaml"},
                "big_flash": {"path": "assets/lights/big_flash.yaml"},
                "reload": {"path": "assets/lights/reload.yaml"},
            },
        }
        return gun, weapon

    def build_burst_shot(self) -> tuple[dict, dict]:
        gun = self.build_common_gun()
        weapon = {
            "weapon": {
                "initial_state": "ready",
                "variables": {
                    "ammo": 9,
                    "mag_capacity": 9,
                    "burst_count": 0,
                    "burst_size": 3,
                },
                "states": [
                    {"id": "ready", "label": "Ready"},
                    {
                        "id": "bursting",
                        "label": "Bursting",
                        "on_entry": [
                            {"type": "play_audio", "clip": "burst_shot", "interrupt": "interrupt"},
                            {"type": "start_light_sequence", "sequence": "muzzle_flash"},
                            {"type": "adjust_ammo", "delta": -1},
                            {"type": "add_var", "name": "burst_count", "value": 1},
                            {"type": "schedule_event", "event": "fire_tick", "delay_ms": 75},
                        ],
                    },
                    {
                        "id": "reloading",
                        "label": "Reloading",
                        "on_entry": [
                            {"type": "stop_audio"},
                            {"type": "stop_light_sequence"},
                            {"type": "set_var", "name": "burst_count", "value": 0},
                            {"type": "play_audio", "clip": "reload", "interrupt": "interrupt"},
                            {"type": "start_light_sequence", "sequence": "reload"},
                            {"type": "schedule_event", "event": "reload_complete", "delay_ms": 1200},
                        ],
                    },
                    {"id": "empty", "label": "Empty"},
                ],
                "transitions": [
                    {
                        "id": "start_burst",
                        "source": "ready",
                        "trigger": "trigger_pressed",
                        "target": "bursting",
                        "guard": {"var_gt": {"name": "ammo", "value": 0}},
                        "actions": [
                            {"type": "set_var", "name": "burst_count", "value": 0},
                        ],
                    },
                    {
                        "id": "pull_on_empty",
                        "source": "ready",
                        "trigger": "trigger_pressed",
                        "target": "empty",
                        "guard": {"var_lte": {"name": "ammo", "value": 0}},
                    },
                    {
                        "id": "continue_burst",
                        "source": "bursting",
                        "trigger": "fire_tick",
                        "target": "bursting",
                        "guard": {
                            "all": [
                                {"var_lt": {"name": "burst_count", "value_from_var": "burst_size"}},
                                {"var_gt": {"name": "ammo", "value": 0}},
                            ]
                        },
                    },
                    {
                        "id": "burst_complete_ready",
                        "source": "bursting",
                        "trigger": "fire_tick",
                        "target": "ready",
                        "guard": {
                            "all": [
                                {"var_gte": {"name": "burst_count", "value_from_var": "burst_size"}},
                                {"var_gt": {"name": "ammo", "value": 0}},
                            ]
                        },
                        "actions": [
                            {"type": "set_var", "name": "burst_count", "value": 0},
                        ],
                    },
                    {
                        "id": "burst_complete_empty",
                        "source": "bursting",
                        "trigger": "fire_tick",
                        "target": "empty",
                        "guard": {"var_lte": {"name": "ammo", "value": 0}},
                        "actions": [
                            {"type": "set_var", "name": "burst_count", "value": 0},
                        ],
                    },
                    {
                        "id": "reload_from_ready",
                        "source": "ready",
                        "trigger": "reload_pressed",
                        "target": "reloading",
                    },
                    {
                        "id": "reload_from_empty",
                        "source": "empty",
                        "trigger": "reload_pressed",
                        "target": "reloading",
                    },
                    {
                        "id": "reload_done",
                        "source": "reloading",
                        "trigger": "reload_complete",
                        "target": "ready",
                        "actions": [
                            {"type": "set_ammo_full"},
                        ],
                    },
                ],
            },
            "clips": {
                "burst_shot": {"path": "assets/audio/burst/shot.wav"},
                "reload": {"path": "assets/audio/shared/reload.wav"},
            },
            "light_sequences": {
                "muzzle_flash": {"path": "assets/lights/muzzle_flash.yaml"},
                "reload": {"path": "assets/lights/reload.yaml"},
            },
        }
        return gun, weapon

    def write_demo(self, output_dir: str | Path, name: str, gun: dict, weapon: dict) -> tuple[Path, Path]:
        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)

        gun_path = output_root / (name + "_gun.yaml")
        weapon_path = output_root / (name + "_weapon.yaml")

        gun_path.write_text(yaml.safe_dump(gun, sort_keys=False), encoding="utf-8")
        weapon_path.write_text(yaml.safe_dump(weapon, sort_keys=False), encoding="utf-8")
        return gun_path, weapon_path
