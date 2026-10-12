"""Validate the two CPX-61 layouts, their wiring orders and demo selection."""
from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = (
    ROOT / "libs/weapon_fsm_lights/examples/layouts",
    ROOT / "src/weapon_fsm_workspace/demos/assets/lights/layouts",
)
LAYOUT_NAMES = ("cpx_ring_61.json", "cpx_ring_61_outside_in.json")
RINGS = (1, 8, 12, 16, 24)


def rings_for(document):
    leds = sorted(document["leds"], key=lambda led: led["index"])
    assert [led["index"] for led in leds] == list(range(61))
    distances = [math.hypot(led["u"] - .5, led["v"] - .5) for led in leds]
    return distances, leds


class CpxRing61LayoutTests(unittest.TestCase):
    def test_both_layouts_exist_and_match_between_editor_sources(self):
        for filename in LAYOUT_NAMES:
            layouts = [json.loads((directory / filename).read_text(encoding="utf-8")) for directory in DIRECTORIES]
            self.assertEqual(layouts[0], layouts[1])

    def test_opposite_wiring_indices_preserve_physical_geometry(self):
        inside = json.loads((DIRECTORIES[0] / LAYOUT_NAMES[0]).read_text(encoding="utf-8"))
        outside = json.loads((DIRECTORIES[0] / LAYOUT_NAMES[1]).read_text(encoding="utf-8"))
        inside_dist, inside_leds = rings_for(inside)
        outside_dist, outside_leds = rings_for(outside)
        self.assertEqual((inside_leds[0]["u"], inside_leds[0]["v"]), (.5, .5))
        self.assertEqual((outside_leds[-1]["u"], outside_leds[-1]["v"]), (.5, .5))
        self.assertLess(inside_dist[0], inside_dist[-1])
        self.assertGreater(outside_dist[0], outside_dist[-1])
        self.assertEqual(sorted((led["u"], led["v"]) for led in inside_leds),
                         sorted((led["u"], led["v"]) for led in outside_leds))
        for distances, counts, descending in ((inside_dist, RINGS, False), (outside_dist, reversed(RINGS), True)):
            offset = 0
            radii = []
            for count in counts:
                ring = distances[offset:offset + count]
                self.assertLess(max(ring) - min(ring), .00002)
                radii.append(sum(ring) / count)
                offset += count
            self.assertEqual(offset, 61)
            self.assertTrue(all((a > b if descending else a < b) for a, b in zip(radii, radii[1:])))

    def test_wired_demos_choose_outside_in(self):
        base = ROOT / "src/weapon_fsm_workspace/demos/assets/lights"
        for name in ("idle_glow", "rainbow_ring_61", "metroid-prime-lights"):
            project = yaml.safe_load((base / f"{name}.yaml").read_text(encoding="utf-8"))
            self.assertEqual(project["layout"]["path"], "layouts/cpx_ring_61_outside_in.json")
        frames = yaml.safe_load((base / "idle_glow.yaml").read_text(encoding="utf-8"))["frames"]
        self.assertEqual(set(frames[0]["leds"]), {"60"})


if __name__ == "__main__":
    unittest.main()
