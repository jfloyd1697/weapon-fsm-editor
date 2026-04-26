import html
import json
from typing import Optional

from pyvis.network import Network

from weapon_fsm_core.domain.model import WeaponConfig


class MachineHtmlBuilder:
    def __init__(self, title: str, runtime_js_name: str = "runtime.js") -> None:
        self._title = title
        self._runtime_js_name = runtime_js_name

    def build_html(
        self,
        machine: WeaponConfig,
        active_state_id: Optional[str] = None,
        valid_transition_ids: Optional[set[str]] = None,
        last_transition_id: Optional[str] = None,
    ) -> str:
        valid_transition_ids = valid_transition_ids or set()

        net = Network(
            height="100vh",
            width="100%",
            directed=True,
            bgcolor="#1e1e1e",
            font_color="#e6edf3",
            cdn_resources="in_line",
        )

        net.set_options(self._options_json())

        for state in machine.states:
            net.add_node(
                state.id,
                label=state.label or state.id,
                title=html.escape(state.id),
                shape="box",
                color=self._node_color(state.id, active_state_id),
                borderWidth=2,
                font={
                    "color": "#e6edf3",
                    "face": "Segoe UI, Arial, sans-serif",
                    "size": 16,
                },
                margin=18,
            )

        route_counts = {}
        for transition in machine.transitions:
            key = (transition.source, transition.target)
            route_index = route_counts.get(key, 0)
            route_counts[key] = route_index + 1
            edge_color, edge_width = self._edge_style(
                transition.id,
                valid_transition_ids,
                last_transition_id,
            )
            roundness = self._roundness_for_route(
                transition.source,
                transition.target,
                route_index,
            )

            net.add_edge(
                transition.source,
                transition.target,
                id=transition.id,
                label=transition.trigger or transition.id,
                title=html.escape(transition.id),
                arrows="to",
                color=edge_color,
                width=edge_width,
                smooth={
                    "enabled": True,
                    "type": "curvedCW" if roundness >= 0 else "curvedCCW",
                    "roundness": abs(roundness),
                },
                font={
                    "color": "#e6edf3",
                    "face": "Segoe UI, Arial, sans-serif",
                    "size": 14,
                    "background": "#1e1e1e",
                    "strokeWidth": 0,
                    "align": "horizontal",
                    "vadjust": -10,
                },
            )

        raw_html = net.generate_html(notebook=False)
        return self._patch_html(raw_html)

    def _node_color(self, state_id: str, active_state_id: Optional[str]) -> dict:
        if state_id == active_state_id:
            return {
                "background": "#2f81f7",
                "border": "#79c0ff",
                "highlight": {"background": "#2f81f7", "border": "#79c0ff"},
                "hover": {"background": "#2f81f7", "border": "#79c0ff"},
            }
        return {
            "background": "#243447",
            "border": "#6e7681",
            "highlight": {"background": "#243447", "border": "#6e7681"},
            "hover": {"background": "#2d4158", "border": "#8b949e"},
        }

    def _edge_style(
        self,
        transition_id: str,
        valid_transition_ids: set[str],
        last_transition_id: Optional[str],
    ) -> tuple[str, int]:
        if transition_id == last_transition_id:
            return "#4ea1ff", 4
        if transition_id in valid_transition_ids:
            return "#e3b341", 3
        return "#8b949e", 2

    def _roundness_for_route(self, source_id: str, target_id: str, route_index: int) -> float:
        if source_id == target_id:
            return 0.35
        if route_index == 0:
            return 0.18
        direction = 1.0 if route_index % 2 else -1.0
        magnitude = 0.18 + 0.08 * (route_index // 2)
        return direction * magnitude

    def _options_json(self) -> str:
        return json.dumps(
            {
                "autoResize": True,
                "layout": {"hierarchical": {"enabled": False}},
                "interaction": {
                    "hover": True,
                    "dragView": True,
                    "dragNodes": True,
                    "zoomView": True,
                    "navigationButtons": False,
                    "keyboard": False,
                },
                "physics": {"enabled": False},
                "nodes": {"shape": "box"},
                "edges": {
                    "smooth": {
                        "enabled": True,
                        "type": "dynamic",
                        "roundness": 0.18,
                    },
                    "selectionWidth": 0,
                    "hoverWidth": 0,
                    "font": {
                        "align": "horizontal",
                        "vadjust": -10,
                    },
                },
            }
        )

    def _patch_html(self, raw_html: str) -> str:
        css_patch = f"""
<style>
html, body {{
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
    overflow: hidden;
    background: #1e1e1e;
}}

#mynetwork {{
    width: 100% !important;
    height: 100vh !important;
    background: #1e1e1e !important;
    border: none !important;
}}

.card {{
    margin: 0 !important;
    border: none !important;
    background: #1e1e1e !important;
}}

.card-body {{
    padding: 0 !important;
    background: #1e1e1e !important;
}}
</style>
"""

        script_patch = f'<script src="{self._runtime_js_name}"></script>'

        if "</head>" in raw_html:
            raw_html = raw_html.replace("</head>", css_patch + "\n</head>", 1)

        if "</body>" in raw_html:
            raw_html = raw_html.replace("</body>", script_patch + "\n</body>", 1)
        else:
            raw_html += script_patch

        return raw_html
