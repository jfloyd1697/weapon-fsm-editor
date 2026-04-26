from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .application.builders import WeaponProfileBuilder, ActionFactory
    from .application.simulate_event import SimulationService
    from .infrastructure.yaml.repositories import ProfileRepository
    from .infrastructure.yaml.profile_mapper import ProfileYamlMapper
    from .infrastructure.yaml.profile_builder import ProfileYamlBuilder

__all__ = [
    "ActionFactory",
    "WeaponProfileBuilder",
    "SimulationService",
    "ProfileRepository",
    "ProfileYamlMapper",
]


def __getattr__(name: str):
    if name in {"ActionFactory", "WeaponProfileBuilder"}:
        from .application.builders import WeaponProfileBuilder, ActionFactory

        return {"ActionFactory": ActionFactory, "WeaponProfileBuilder": WeaponProfileBuilder}[name]

    if name == "SimulationService":
        from .application.simulate_event import SimulationService

        return SimulationService

    if name == "ProfileRepository":
        from .infrastructure.yaml.repositories import ProfileRepository

        return ProfileRepository

    if name == "ProfileYamlMapper":
        from .infrastructure.yaml.profile_mapper import ProfileYamlMapper

        return ProfileYamlMapper

    if name == "ProfileYamlBuilder":
        from .infrastructure.yaml.profile_builder import ProfileYamlBuilder

        return ProfileYamlBuilder

    raise AttributeError(name)
