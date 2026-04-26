from weapon_fsm_audio import AudioConfigBuilder
from weapon_fsm_core.application.builders import ActionFactory, WeaponProfileBuilder


class WeaponPresetDirector:
    def build_default_gun(self):
        builder = WeaponProfileBuilder()
        audio = AudioConfigBuilder(builder)
        builder.set_events(["trigger_pressed", "reload_pressed", "reload_finished", "fire_done"])
        builder.set_initial_state("ready")
        builder.ensure_state("ready", "Ready")
        builder.ensure_state("firing", "Firing")
        builder.ensure_state("reloading", "Reloading")
        audio.set_clip("shot", "assets/audio/default/shot.wav")
        audio.set_clip("reload", "assets/audio/default/reload.wav")
        audio.set_effect("fire_effect", clip="shot")
        audio.set_effect("reload_effect", clip="reload")
        builder.add_transition("fire", "ready", "trigger_pressed", "firing")
        audio.bind_transition_effect("fire", "fire_effect")
        builder.append_transition_action("fire", ActionFactory.schedule_event("fire_done", 120))
        builder.add_transition("fire_done", "firing", "fire_done", "ready")

        builder.add_transition("reload", "ready", "reload_pressed", "reloading")
        audio.bind_transition_effect("reload", "reload_effect")
        builder.append_transition_action("reload", ActionFactory.schedule_event("reload_finished", 700))
        builder.add_transition("reload_done", "reloading", "reload_finished", "ready")

        return builder.build_gun(), builder.build_weapon()
