from weapon_fsm_core.domain.model import (
    ActionDef,
    EventDef,
    GuardDef,
    GunConfig,
    StateDef,
    TransitionDef,
    WeaponConfig,
)
from .profile_schema import ActionFile, GuardFile, GunFile, StateFile, TransitionFile, WeaponFile


def gun_file_to_domain(gun: GunFile) -> GunConfig:
    return GunConfig(
        events={event.id: EventDef(id=event.id, label=event.label, kind=event.kind) for event in gun.events},
    )


def weapon_file_to_domain(weapon: WeaponFile) -> WeaponConfig:
    return WeaponConfig(
        mag_capacity=weapon.mag_capacity,
        initial_ammo=weapon.initial_ammo,
        initial_state=weapon.initial_state,
        states={state.id: _state_file_to_domain(state) for state in weapon.states},
        transitions=tuple(_transition_file_to_domain(transition) for transition in weapon.transitions),
    )


def _state_file_to_domain(state: StateFile) -> StateDef:
    return StateDef(
        id=state.id,
        label=state.label,
        on_entry=tuple(_action_file_to_domain(action) for action in state.on_entry),
        on_exit=tuple(_action_file_to_domain(action) for action in state.on_exit),
    )


def _transition_file_to_domain(transition: TransitionFile) -> TransitionDef:
    return TransitionDef(
        id=transition.id,
        source=transition.source,
        target=transition.target,
        trigger=transition.trigger,
        actions=tuple(_action_file_to_domain(action) for action in transition.actions),
        guard=_guard_file_to_domain(transition.guard),
    )


def _action_file_to_domain(action: ActionFile) -> ActionDef:
    arguments = dict(action.arguments)
    for key in ("sound", "clip", "pattern", "sequence", "event", "delay_ms", "delta", "value", "interrupt"):
        value = getattr(action, key)
        if value is not None:
            arguments[key] = value
    if action.clips:
        arguments["clips"] = list(action.clips)
    return ActionDef(type=action.type, arguments=arguments)


def _guard_file_to_domain(guard: GuardFile | None) -> GuardDef | None:
    if guard is None:
        return None
    return GuardDef(
        ammo_gt=guard.ammo_gt,
        ammo_gte=guard.ammo_gte,
        ammo_eq=guard.ammo_eq,
        ammo_lt=guard.ammo_lt,
        ammo_lte=guard.ammo_lte,
        trigger_pressed=guard.trigger_pressed,
        all=tuple(filter(None, (_guard_file_to_domain(item) for item in guard.all))),
        any=tuple(filter(None, (_guard_file_to_domain(item) for item in guard.any))),
    )
