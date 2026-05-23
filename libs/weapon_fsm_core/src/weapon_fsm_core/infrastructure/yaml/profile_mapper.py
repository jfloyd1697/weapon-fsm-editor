from pathlib import Path

import yaml

from weapon_fsm_core.domain.model import ActionDef, WeaponConfig, GunConfig


class ProfileYamlMapper:
    @staticmethod
    def _action_to_dict(action: ActionDef) -> dict[str, object]:
        data = {"type": action.type}
        data.update(action.arguments)
        return data

    @staticmethod
    def gun_to_dict(gun: GunConfig) -> dict[str, object]:
        return {
            "gun": {
                "events": [{"id": event_id} for event_id in gun.events],
            }
        }

    @staticmethod
    def weapon_to_dict(weapon: WeaponConfig) -> dict[str, object]:
        return {
            "clips": {
                name: {"path": clip.path, "preload": clip.preload}
                for name, clip in weapon.clips.items()
            },
            "clip_sets": {
                name: {"clips": list(clip_set.clips), "mode": clip_set.mode}
                for name, clip_set in weapon.clip_sets.items()
            },
            "audio_effects": {
                name: {
                    "clips": list(effect.clips),
                    "mode": effect.mode,
                    "interrupt": effect.interrupt,
                    "loop": effect.loop,
                    "gain": effect.gain,
                }
                for name, effect in weapon.audio_effects.items()
            },
            "light_sequences": {
                name: {"path": sequence.path, "preload": sequence.preload}
                for name, sequence in weapon.light_sequences.items()
            },
            "weapon": {
                "initial_state": weapon.initial_state,
                "variables": dict(weapon.variables),
                "states": [
                    {
                        "id": state.id,
                        "label": state.label,
                        "on_entry": [ProfileYamlMapper._action_to_dict(action) for action in state.on_entry],
                        "on_exit": [ProfileYamlMapper._action_to_dict(action) for action in state.on_exit],
                    }
                    for state in weapon.states.values()
                ],
                "transitions": [
                    {
                        "id": transition.id,
                        "source": transition.source,
                        "trigger": transition.trigger,
                        "target": transition.target,
                        "guard": None if transition.guard is None else {
                            key: value
                            for key, value in {
                                "all": [g for g in transition.guard.all],
                                "any": [g for g in transition.guard.any],
                                "trigger_pressed": transition.guard.trigger_pressed,
                                "var_eq": transition.guard.var_eq,
                                "var_gt": transition.guard.var_gt,
                                "var_gte": transition.guard.var_gte,
                                "var_lt": transition.guard.var_lt,
                                "var_lte": transition.guard.var_lte,
                            }.items()
                            if value not in (None, [], ())
                        },
                        "actions": [ProfileYamlMapper._action_to_dict(action) for action in transition.actions],
                    }
                    for transition in weapon.transitions
                ],
            },
        }


    @staticmethod
    def gun_to_text(gun):
        return yaml.safe_dump(recursive_filter_empty(ProfileYamlMapper.gun_to_dict(gun)), sort_keys=False)

    def write_gun(cls, gun: GunConfig, path: str | Path) -> Path:
        out_path = Path(path)
        out_path.write_text(cls.gun_to_text(gun), encoding="utf-8")
        return out_path

    @staticmethod
    def weapon_to_text(weapon):
        weapon_data = recursive_filter_empty(ProfileYamlMapper.weapon_to_dict(weapon))
        return yaml.safe_dump(weapon_data, sort_keys=False)

    @classmethod
    def write_weapon(cls, weapon: WeaponConfig, path: str | Path) -> Path:
        out_path = Path(path)
        out_path.write_text(cls.weapon_to_text(weapon), encoding="utf-8")
        return out_path


def recursive_filter_empty(data: dict):
    filtered_data = {}

    for key, value in data.items():
        if isinstance(value, dict) and value:
            filtered_data[key] = recursive_filter_empty(value)
        elif isinstance(value, list) and value:
            filtered_data[key] = [recursive_filter_empty(item) if isinstance(item, dict) else item for item in value if item]
        elif value:
            filtered_data[key] = value

    return filtered_data
