from weapon_fsm_core.domain.model import ActionDef, EventDef, GuardDef, GunConfig, StateDef, TransitionDef, WeaponConfig
from weapon_fsm_core.domain.validation import ProfileValidator


def test_validator_reports_unknown_trigger() -> None:
    gun = GunConfig(events={"trigger_pressed": EventDef(id="trigger_pressed")})
    weapon = WeaponConfig(
        mag_capacity=5,
        initial_ammo=5,
        initial_state="ready",
        states={"ready": StateDef(id="ready", label="Ready")},
        transitions=(
            TransitionDef(
                id="bad",
                source="ready",
                target="ready",
                trigger="not_real",
            ),
        ),
    )

    issues = ProfileValidator().validate(gun, weapon)

    assert any("Unknown trigger 'not_real'" in issue.message for issue in issues)


def test_validator_accepts_scheduled_event_from_action() -> None:
    gun = GunConfig(events={"trigger_pressed": EventDef(id="trigger_pressed")})
    weapon = WeaponConfig(
        mag_capacity=5,
        initial_ammo=5,
        initial_state="ready",
        states={
            "ready": StateDef(id="ready", label="Ready"),
            "firing": StateDef(
                id="firing",
                label="Firing",
                on_entry=(ActionDef(type="schedule_event", arguments={"event": "fire_complete", "delay_ms": 80}),),
            ),
        },
        transitions=(
            TransitionDef(
                id="fire",
                source="ready",
                target="firing",
                trigger="trigger_pressed",
            ),
            TransitionDef(
                id="done",
                source="firing",
                target="ready",
                trigger="fire_complete",
                guard=GuardDef(ammo_gte=0),
            ),
        ),
    )

    issues = ProfileValidator().validate(gun, weapon)
    assert not issues
