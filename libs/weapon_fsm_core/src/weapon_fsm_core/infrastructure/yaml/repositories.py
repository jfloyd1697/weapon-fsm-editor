from typing import Any

import yaml

from weapon_fsm_core.domain.model import ActionDef, GunConfig, GuardDef, StateDef, TransitionDef, WeaponConfig


class ProfileRepository:
    def load_gun_text(self, text: str) -> GunConfig:
        raw = yaml.safe_load(text) or {}
        gun_raw = raw.get("gun", raw)

        event_ids: list[str] = []
        for item in gun_raw.get("events", []):
            if isinstance(item, dict):
                event_id = item.get("id")
            else:
                event_id = item
            if event_id:
                event_ids.append(str(event_id))

        return GunConfig(events=tuple(event_ids))

    def load_weapon_text(self, text: str) -> WeaponConfig:
        raw = yaml.safe_load(text) or {}
        weapon_raw = raw.get("weapon", raw)
        states = self._parse_states(weapon_raw.get("states", []))
        transitions = self._parse_transitions(weapon_raw.get("transitions", []))
        variables = dict(weapon_raw.get("variables", {}))

        return WeaponConfig(
            initial_state=str(weapon_raw["initial_state"]),
            variables=variables,
            states=states,
            transitions=tuple(transitions),
        )

    def _parse_states(self, raw_states: list[dict[str, Any]]) -> dict[str, StateDef]:
        states: dict[str, StateDef] = {}

        for raw_state in raw_states:
            state = StateDef(
                id=str(raw_state["id"]),
                label=str(raw_state.get("label", raw_state["id"])),
                on_entry=self._parse_actions(raw_state.get("on_entry", [])),
                on_exit=self._parse_actions(raw_state.get("on_exit", [])),
            )
            states[state.id] = state

        return states

    def _parse_transitions(
        self,
        raw_transitions: list[dict[str, Any]],
    ) -> list[TransitionDef]:
        transitions: list[TransitionDef] = []

        for raw_transition in raw_transitions:
            transitions.append(
                TransitionDef(
                    id=str(raw_transition["id"]),
                    source=str(raw_transition["source"]),
                    trigger=str(raw_transition["trigger"]),
                    target=str(raw_transition["target"]),
                    guard=self._parse_guard(raw_transition.get("guard")),
                    actions=self._parse_actions(raw_transition.get("actions", [])),
                )
            )

        return transitions

    def _parse_actions(self, raw_actions: list[dict[str, Any]]) -> tuple[ActionDef, ...]:
        actions: list[ActionDef] = []

        for raw_action in raw_actions:
            action_type = str(raw_action["type"])
            arguments = {
                key: value
                for key, value in raw_action.items()
                if key != "type"
            }
            actions.append(ActionDef(type=action_type, arguments=arguments))

        return tuple(actions)

    def _parse_guard(self, raw: dict[str, Any] | None) -> GuardDef | None:
        if not raw:
            return None

        all_items = tuple(
            item for item in (self._parse_guard(entry) for entry in raw.get("all", []))
            if item is not None
        )
        any_items = tuple(
            item for item in (self._parse_guard(entry) for entry in raw.get("any", []))
            if item is not None
        )

        return GuardDef(
            all=all_items,
            any=any_items,
            trigger_pressed=raw.get("trigger_pressed"),
            var_eq=raw.get("var_eq"),
            var_gt=raw.get("var_gt"),
            var_gte=raw.get("var_gte"),
            var_lt=raw.get("var_lt"),
            var_lte=raw.get("var_lte"),
        )