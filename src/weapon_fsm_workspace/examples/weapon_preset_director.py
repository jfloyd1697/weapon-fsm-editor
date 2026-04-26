from weapon_fsm_audio.application import AudioConfigBuilder
from weapon_fsm_core.application.builders import ActionFactory, WeaponProfileBuilder
from weapon_fsm_core.domain.model import WeaponConfig, GunConfig


class WeaponPresetDirector:
    def build_default_gun(self) -> WeaponConfig:
        builder = WeaponProfileBuilder()
        audio = AudioConfigBuilder(builder)

        builder.set_events(["trigger_pressed", "reload_pressed", "reload_finished"])
        builder.set_initial_state("ready")

        builder.ensure_state("ready", "Ready")
        builder.ensure_state("reloading", "Reloading")

        audio.set_clip("shot", "assets/audio/default/shot.wav")
        audio.set_clip("reload", "assets/audio/default/reload.wav")

        builder.add_transition("fire", "ready", "trigger_pressed", "ready")
        builder.append_transition_action("fire", ActionFactory.play_audio("shot"))

        builder.add_transition("reload", "ready", "reload_pressed", "reloading")
        builder.append_transition_action("reload", ActionFactory.play_audio("reload"))

        builder.add_transition("reload_done", "reloading", "reload_finished", "ready")

        return builder.build_weapon()

    def build_charge_shot(self) -> WeaponConfig:
        builder = WeaponProfileBuilder()
        audio = AudioConfigBuilder(builder)

        builder.set_events(
            ["trigger_pressed", "trigger_released", "charge_complete", "fire_done"]
        )
        builder.set_initial_state("ready")

        builder.ensure_state("ready", "Ready")
        builder.ensure_state("charging", "Charging")
        builder.ensure_state("charged", "Charged")
        builder.ensure_state("firing", "Firing")

        audio.set_clip("charge_loop", "assets/audio/charge/charge_loop.wav")
        audio.set_clip("charge_fail", "assets/audio/charge/charge_fail.wav")
        audio.set_clip("charge_fire", "assets/audio/charge/charge_fire.wav")

        builder.add_transition("start_charge", "ready", "trigger_pressed", "charging")
        builder.append_transition_action("start_charge", ActionFactory.play_audio_loop("charge_loop"))

        builder.add_transition("charge_done", "charging", "charge_complete", "charged")

        builder.add_transition("release_early", "charging", "trigger_released", "ready")
        builder.append_transition_action("release_early", ActionFactory.stop_audio())
        builder.append_transition_action("release_early", ActionFactory.play_audio("charge_fail"))

        builder.add_transition("release_full", "charged", "trigger_released", "firing")
        builder.append_transition_action("release_full", ActionFactory.stop_audio())
        builder.append_transition_action("release_full", ActionFactory.play_audio("charge_fire"))

        builder.add_transition("fire_done", "firing", "fire_done", "ready")

        return builder.build_weapon()

    def build_all(self):
        presets = {}
        presets["default"] = self.build_default_gun()
        presets["charge_shot"] = self.build_charge_shot()
        return presets
