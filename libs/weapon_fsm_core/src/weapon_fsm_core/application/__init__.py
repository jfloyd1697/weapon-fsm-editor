__all__ = ["ActionFactory", "WeaponProfileBuilder", "DispatchRecord", "SimulationService"]


def __getattr__(name: str):
    if name in {"ActionFactory", "WeaponProfileBuilder"}:
        from .builders import WeaponProfileBuilder
        from weapon_fsm_core import ActionFactory

        return {"ActionFactory": ActionFactory, "WeaponProfileBuilder": WeaponProfileBuilder}[name]

    if name in {"DispatchRecord", "SimulationService"}:
        from .simulate_event import DispatchRecord, SimulationService

        return {"DispatchRecord": DispatchRecord, "SimulationService": SimulationService}[name]

    raise AttributeError(name)
