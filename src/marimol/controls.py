from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import marimo as mo
from marimo._output.hypertext import Html
from marimo._plugins.ui._impl.batch import _batch_base

from .utils import dict_to_toml, resolve_color

if TYPE_CHECKING:
    from .viewer import MoleculeViewerWidget

BACKGROUND_PRESETS: dict[str, str] = {
    "Clean White": "#ffffff",
    "Slate Dark": "#0f172a",
    "Midnight Black": "#000000",
    "Charcoal": "#1e1e1e",
    "Soft Gray": "#f1f5f9",
    "Navy": "#0b192c",
    "Emerald Dark": "#062822",
    "Warm Cream": "#faf8f5",
    "Transparent": "transparent",
}

OUTLINE_PRESETS: dict[str, Any] = {
    "None": False,
    "1px Solid (Slate)": "1px solid #334155",
    "1px Solid (Light)": "1px solid #e2e8f0",
    "1px Solid (Gray)": "1px solid #ccc",
    "2px Solid (Blue)": "2px solid #3b82f6",
    "Default Border": True,
}

SPIN_AXIS_PRESETS: dict[str, list[float]] = {
    "Y-axis [0, 1, 0]": [0.0, 1.0, 0.0],
    "X-axis [1, 0, 0]": [1.0, 0.0, 0.0],
    "Z-axis [0, 0, 1]": [0.0, 0.0, 1.0],
    "Diagonal [1, 1, 0]": [1.0, 1.0, 0.0],
}

VECTOR_COLOR_PRESETS: dict[str, str] = {
    "Red": "red",
    "Yellow": "yellow",
    "Cyan": "cyan",
    "Green": "green",
    "Blue": "blue",
    "Magenta": "magenta",
    "Orange": "orange",
    "White": "white",
    "Black": "black",
}

DPI_PRESETS: dict[str, int] = {
    "100 DPI (Standard)": 100,
    "150 DPI (Medium)": 150,
    "200 DPI (High, default)": 200,
    "300 DPI (Publication)": 300,
    "400 DPI (Ultra)": 400,
}


def _extract_widget(viewer: MoleculeViewerWidget | Any) -> MoleculeViewerWidget:
    """Extract the underlying MoleculeViewerWidget from a widget or marimo UI wrapper."""
    if hasattr(viewer, "widget") and viewer.widget is not None:
        return viewer.widget  # type: ignore[no-any-return]
    return viewer  # type: ignore[no-any-return]


def get_viewer_config(w: MoleculeViewerWidget) -> dict[str, Any]:
    """
    Extract the current configuration dictionary from a MoleculeViewerWidget.

    *(added in v0.4.0)*
    """
    style_val: Any = w.style
    if isinstance(style_val, dict):
        if style_val.get("use_vdw_radii", False):
            style_val = "vdw"
        elif style_val.get("bond_radius") == 0.05 and style_val.get("fixed_atomic_radius") == 0.05:
            style_val = "wireframe"
        elif style_val.get("bond_radius") == 0.15 and style_val.get("fixed_atomic_radius") == 0.45:
            style_val = "ball-and-stick"

    return {
        "style": style_val,
        "background_color": getattr(w, "background_color", "#ffffff"),
        "show_axes": getattr(w, "show_axes", False),
        "projection": getattr(w, "projection", "orthographic"),
        "width": getattr(w, "width", "100%"),
        "height": getattr(w, "height", "400px"),
        "viewer_outline": getattr(w, "viewer_outline", False),
        "fog": getattr(w, "fog", False),
        "fog_strength": getattr(w, "fog_strength", 0.5),
        "clip_distance": getattr(w, "clip_distance", 0.0) or 0.0,
        "draw_outlines": getattr(w, "draw_outlines", False),
        "draw_labels": getattr(w, "draw_labels", False),
        "measuring_tool": getattr(w, "measuring_tool", False),
        "structure_transparency": getattr(w, "structure_transparency", 0.0),
        "vector_width": getattr(w, "vector_width", 0.08),
        "vector_outline": getattr(w, "vector_outline", False),
        "vector_color": getattr(w, "vector_color", "red"),
        "spin": getattr(w, "spin", False),
        "spin_axis": list(getattr(w, "spin_axis", [0.0, 1.0, 0.0])),
        "spin_speed": getattr(w, "spin_speed", 2.0),
        "multi_traj": getattr(w, "multi_traj", True),
        "traj_fps": getattr(w, "traj_fps", 10.0),
        "trajectory_slider": getattr(w, "trajectory_slider", False),
        "show_help": getattr(w, "show_help", True),
        "recording_tools": getattr(w, "recording_tools", False),
        "dpi": getattr(w, "dpi", 200),
        "record_include_bgd": getattr(w, "record_include_bgd", False),
        "record_include_ui": getattr(w, "record_include_ui", False),
    }


class MoleculeViewerControls(_batch_base):
    """
    Interactive marimo UI control panel for MoleculeViewerWidget.

    Enables non-destructive real-time adjustment of all viewer properties (such as background color,
    render style, spin, projection, outlines, atom labels, and transparency) via WebSockets without
    triggering notebook cell re-runs or resetting the 3D camera orientation.

    Inherits from marimo's UIElement so that downstream notebook cells reading `panel.to_toml()`,
    `panel.to_dict()`, or `panel.value` automatically and reactively re-run when any control is modified.

    *(added in v0.4.0)*
    """

    def __init__(
        self,
        widget: MoleculeViewerWidget,
        elements: dict[str, Any],
        layout: Any,
        layout_name: str = "grid",
    ) -> None:
        self._widget = widget
        self._layout = layout
        self._layout_name = layout_name

        html_obj = layout if isinstance(layout, Html) else Html(str(layout))

        super().__init__(
            html=html_obj,
            elements=elements,
            label="Molecule Viewer Controls",
        )

        for name, elem in self._elements.items():
            setattr(self, name, elem)

    @property
    def widget(self) -> MoleculeViewerWidget:
        """The underlying MoleculeViewerWidget instance connected to these controls."""
        return self._widget

    @property
    def layout(self) -> Any:
        """The root marimo layout component (e.g. mo.hstack, mo.vstack, mo.accordion, mo.ui.tabs)."""
        return self._layout

    @property
    def layout_name(self) -> str:
        """The layout style name ('grid', 'accordion', 'tabs', 'vertical', 'horizontal')."""
        return self._layout_name

    @property
    def config(self) -> dict[str, Any]:
        """Current configuration dictionary (reactively tracked in marimo)."""
        return self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        """
        Extract the current viewer configuration as a dictionary.

        Returns
        -------
        dict
            Configuration settings dictionary matching DEFAULT_VIEWER_CONFIG.
        """
        return get_viewer_config(self._widget)

    def to_toml(self) -> str:
        """
        Extract the current viewer configuration as a formatted TOML string.

        Returns
        -------
        str
            A TOML formatted string that can be saved to a file or passed to config=...
        """
        return dict_to_toml(self.to_dict())

    def save_toml(self, path: str | os.PathLike) -> None:
        """
        Save the current viewer configuration to a TOML file.

        Parameters
        ----------
        path : str or os.PathLike
            Destination file path.
        """
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_toml())


# --- Builders for Appearance Controls ---


def _build_background_control(w: MoleculeViewerWidget) -> Any:
    """Build background color dropdown."""
    current_bg = str(getattr(w, "background_color", "#ffffff"))
    bg_opts = dict(BACKGROUND_PRESETS)

    initial_key: str | None = None
    for k, v in bg_opts.items():
        if resolve_color(v).lower() == resolve_color(current_bg).lower():
            initial_key = k
            break
    if initial_key is None:
        custom_key = f"Current ({current_bg})"
        bg_opts[custom_key] = current_bg
        initial_key = custom_key

    def _on_bg_change(new_bg: str) -> None:
        if hasattr(w, "set_background_color"):
            w.set_background_color(new_bg)
        else:
            w.background_color = resolve_color(new_bg)

    return mo.ui.dropdown(
        options=bg_opts,
        value=initial_key,
        label="🖼️ Background",
        on_change=_on_bg_change,
    )


def _build_style_control(w: MoleculeViewerWidget) -> Any:
    """Build visualization style dropdown."""
    current_style_val = "ball-and-stick"
    if isinstance(w.style, dict):
        if w.style.get("use_vdw_radii", False):
            current_style_val = "vdw"
        elif w.style.get("bond_radius") == 0.05 and w.style.get("fixed_atomic_radius") == 0.05:
            current_style_val = "wireframe"
    elif isinstance(w.style, str):
        current_style_val = w.style

    def _on_style_change(new_style: str) -> None:
        if hasattr(w, "set_style"):
            w.set_style(new_style)
        else:
            w.style = new_style  # type: ignore[assignment]

    return mo.ui.dropdown(
        options=["ball-and-stick", "vdw", "wireframe"],
        value=current_style_val,
        label="🎨 Style",
        on_change=_on_style_change,
    )


def _build_projection_control(w: MoleculeViewerWidget) -> Any:
    """Build projection mode dropdown."""
    current_proj = getattr(w, "projection", "orthographic")

    def _on_proj_change(new_proj: str) -> None:
        w.projection = str(new_proj)

    return mo.ui.dropdown(
        options=["orthographic", "perspective"],
        value=current_proj,
        label="📷 Projection",
        on_change=_on_proj_change,
    )


def _build_width_control(w: MoleculeViewerWidget) -> Any:
    """Build viewer width dropdown."""
    cur_width = str(getattr(w, "width", "100%"))
    opts = ["100%", "90%", "80%", "800px", "600px", "500px", "400px"]
    if cur_width not in opts:
        opts.insert(0, cur_width)

    def _on_width_change(val: str) -> None:
        w.width = str(val)

    return mo.ui.dropdown(
        options=opts,
        value=cur_width,
        label="↔️ Width",
        on_change=_on_width_change,
    )


def _build_height_control(w: MoleculeViewerWidget) -> Any:
    """Build viewer height dropdown."""
    cur_height = str(getattr(w, "height", "400px"))
    opts = ["300px", "350px", "400px", "450px", "500px", "550px", "600px"]
    if cur_height not in opts:
        opts.insert(0, cur_height)

    def _on_height_change(val: str) -> None:
        w.height = str(val)

    return mo.ui.dropdown(
        options=opts,
        value=cur_height,
        label="↕️ Height",
        on_change=_on_height_change,
    )


def _build_outline_control(w: MoleculeViewerWidget) -> Any:
    """Build viewer outline dropdown."""
    cur_outline = getattr(w, "viewer_outline", False)
    opts = dict(OUTLINE_PRESETS)

    initial_key = "None"
    for k, v in opts.items():
        if v == cur_outline:
            initial_key = k
            break
    if initial_key == "None" and cur_outline:
        custom_key = f"Custom ({cur_outline})"
        opts[custom_key] = cur_outline
        initial_key = custom_key

    def _on_outline_change(val: Any) -> None:
        w.viewer_outline = val

    return mo.ui.dropdown(
        options=opts,
        value=initial_key,
        label="🔲 Viewer Outline",
        on_change=_on_outline_change,
    )


# --- Builders for Motion Controls ---


def _build_spin_control(w: MoleculeViewerWidget) -> Any:
    """Build auto-spin checkbox."""

    def _on_spin_change(val: bool) -> None:
        w.spin = bool(val)

    return mo.ui.checkbox(
        value=bool(getattr(w, "spin", False)),
        label="🔄 Auto-spin",
        on_change=_on_spin_change,
    )


def _build_spin_speed_control(w: MoleculeViewerWidget) -> Any:
    """Build spin speed slider."""

    def _on_spin_speed_change(val: float) -> None:
        w.spin_speed = float(val)

    return mo.ui.slider(
        start=-10.0,
        stop=10.0,
        step=0.5,
        value=float(getattr(w, "spin_speed", 2.0)),
        label="⚡ Spin Speed",
        on_change=_on_spin_speed_change,
    )


def _build_spin_axis_control(w: MoleculeViewerWidget) -> Any:
    """Build spin axis dropdown."""
    cur_axis = list(getattr(w, "spin_axis", [0.0, 1.0, 0.0]))
    opts = dict(SPIN_AXIS_PRESETS)

    initial_key = "Y-axis [0, 1, 0]"
    for k, v in opts.items():
        if v == cur_axis:
            initial_key = k
            break
    if initial_key == "Y-axis [0, 1, 0]" and cur_axis not in opts.values():
        custom_key = f"Custom {cur_axis}"
        opts[custom_key] = cur_axis
        initial_key = custom_key

    def _on_axis_change(val: list[float]) -> None:
        w.spin_axis = list(val)

    return mo.ui.dropdown(
        options=opts,
        value=initial_key,
        label="🧭 Spin Axis",
        on_change=_on_axis_change,
    )


def _build_multi_traj_control(w: MoleculeViewerWidget) -> Any:
    """Build playback buttons toggle."""

    def _on_multi_traj_change(val: bool) -> None:
        w.multi_traj = bool(val)

    return mo.ui.checkbox(
        value=bool(getattr(w, "multi_traj", True)),
        label="⏯️ Playback Controls",
        on_change=_on_multi_traj_change,
    )


def _build_fps_control(w: MoleculeViewerWidget) -> Any:
    """Build trajectory playback FPS slider."""

    def _on_fps_change(val: float) -> None:
        w.traj_fps = float(val)

    return mo.ui.slider(
        start=1.0,
        stop=60.0,
        step=1.0,
        value=float(getattr(w, "traj_fps", 10.0)),
        label="⏱️ Playback FPS",
        on_change=_on_fps_change,
    )


def _build_trajectory_slider_control(w: MoleculeViewerWidget) -> Any:
    """Build trajectory frame slider checkbox."""

    def _on_traj_slider_change(val: bool) -> None:
        w.trajectory_slider = bool(val)

    return mo.ui.checkbox(
        value=bool(getattr(w, "trajectory_slider", False)),
        label="🎚️ Frame Slider",
        on_change=_on_traj_slider_change,
    )


# --- Builders for Display Controls ---


def _build_outlines_control(w: MoleculeViewerWidget) -> Any:
    """Build structure outlines checkbox."""

    def _on_outlines_change(val: bool) -> None:
        w.draw_outlines = bool(val)

    return mo.ui.checkbox(
        value=bool(getattr(w, "draw_outlines", False)),
        label="✏️ Structure outlines",
        on_change=_on_outlines_change,
    )


def _build_labels_control(w: MoleculeViewerWidget) -> Any:
    """Build atom labels checkbox."""

    def _on_labels_change(val: bool) -> None:
        w.draw_labels = bool(val)

    return mo.ui.checkbox(
        value=bool(getattr(w, "draw_labels", False)),
        label="🏷️ Atom Labels",
        on_change=_on_labels_change,
    )


def _build_axes_control(w: MoleculeViewerWidget) -> Any:
    """Build coordinate axes checkbox."""

    def _on_axes_change(val: bool) -> None:
        w.show_axes = bool(val)

    return mo.ui.checkbox(
        value=bool(getattr(w, "show_axes", False)),
        label="🧭 Coordinate Axes",
        on_change=_on_axes_change,
    )


def _build_fog_control(w: MoleculeViewerWidget) -> Any:
    """Build depth fog checkbox."""

    def _on_fog_change(val: bool) -> None:
        w.fog = bool(val)

    return mo.ui.checkbox(
        value=bool(getattr(w, "fog", False)),
        label="🌫️ Fog Effect",
        on_change=_on_fog_change,
    )


def _build_fog_strength_control(w: MoleculeViewerWidget) -> Any:
    """Build fog strength slider."""

    def _on_fog_strength_change(val: float) -> None:
        w.fog_strength = float(val)

    return mo.ui.slider(
        start=0.1,
        stop=1.0,
        step=0.05,
        value=float(getattr(w, "fog_strength", 0.5)),
        label="🌫️ Fog Strength",
        on_change=_on_fog_strength_change,
    )


def _build_clip_distance_control(w: MoleculeViewerWidget) -> Any:
    """Build near clipping plane slider."""

    def _on_clip_change(val: float) -> None:
        w.clip_distance = float(val)

    return mo.ui.slider(
        start=0.0,
        stop=50.0,
        step=0.5,
        value=float(getattr(w, "clip_distance", 0.0) or 0.0),
        label="✂️ Clip Distance (Å)",
        on_change=_on_clip_change,
    )


def _build_transparency_control(w: MoleculeViewerWidget) -> Any:
    """Build structure transparency slider."""

    def _on_transparency_change(val: float) -> None:
        w.structure_transparency = float(val)

    return mo.ui.slider(
        start=0.0,
        stop=1.0,
        step=0.05,
        value=float(getattr(w, "structure_transparency", 0.0)),
        label="👻 Transparency",
        on_change=_on_transparency_change,
    )


def _build_measuring_control(w: MoleculeViewerWidget) -> Any:
    """Build measuring tool checkbox."""

    def _on_measuring_change(val: bool) -> None:
        w.measuring_tool = bool(val)

    return mo.ui.checkbox(
        value=bool(getattr(w, "measuring_tool", False)),
        label="📏 Measuring Tool",
        on_change=_on_measuring_change,
    )


def _build_help_control(w: MoleculeViewerWidget) -> Any:
    """Build help button checkbox."""

    def _on_help_change(val: bool) -> None:
        w.show_help = bool(val)

    return mo.ui.checkbox(
        value=bool(getattr(w, "show_help", True)),
        label="❓ Help Button",
        on_change=_on_help_change,
    )


# --- Builders for Vector Controls ---


def _build_vector_width_control(w: MoleculeViewerWidget) -> Any:
    """Build vector arrow width slider."""

    def _on_vwidth_change(val: float) -> None:
        w.vector_width = float(val)

    return mo.ui.slider(
        start=0.01,
        stop=0.3,
        step=0.01,
        value=float(getattr(w, "vector_width", 0.08)),
        label="🏹 Vector Width",
        on_change=_on_vwidth_change,
    )


def _build_vector_outline_control(w: MoleculeViewerWidget) -> Any:
    """Build vector outline dropdown."""
    cur_out = getattr(w, "vector_outline", False)
    opts = {
        "None": False,
        "Black Outline": "black",
        "White Outline": "white",
        "Default Outline": True,
    }
    initial_key = "None"
    for k, v in opts.items():
        if v == cur_out:
            initial_key = k
            break

    def _on_vout_change(val: Any) -> None:
        w.vector_outline = val

    return mo.ui.dropdown(
        options=opts,
        value=initial_key,
        label="🏹 Vector Outline",
        on_change=_on_vout_change,
    )


def _build_vector_color_control(w: MoleculeViewerWidget) -> Any:
    """Build vector color dropdown."""
    cur_col = str(getattr(w, "vector_color", "red"))
    opts = dict(VECTOR_COLOR_PRESETS)
    initial_key = "Red"
    for k, v in opts.items():
        if resolve_color(v).lower() == resolve_color(cur_col).lower():
            initial_key = k
            break
    if initial_key == "Red" and cur_col not in opts.values():
        custom_key = f"Custom ({cur_col})"
        opts[custom_key] = cur_col
        initial_key = custom_key

    def _on_vcol_change(val: str) -> None:
        w.vector_color = resolve_color(val)

    return mo.ui.dropdown(
        options=opts,
        value=initial_key,
        label="🏹 Vector Color",
        on_change=_on_vcol_change,
    )


# --- Builders for Recording & Capture Controls ---


def _build_recording_tools_control(w: MoleculeViewerWidget) -> Any:
    """Build recording tools toolbar checkbox."""

    def _on_rec_change(val: bool) -> None:
        w.recording_tools = bool(val)

    return mo.ui.checkbox(
        value=bool(getattr(w, "recording_tools", False)),
        label="🎥 Recording Tools",
        on_change=_on_rec_change,
    )


def _build_dpi_control(w: MoleculeViewerWidget) -> Any:
    """Build export DPI dropdown."""
    cur_dpi = int(getattr(w, "dpi", 200))
    opts = dict(DPI_PRESETS)
    initial_key = "200 DPI (High, default)"
    for k, v in opts.items():
        if v == cur_dpi:
            initial_key = k
            break

    def _on_dpi_change(val: int) -> None:
        w.dpi = int(val)

    return mo.ui.dropdown(
        options=opts,
        value=initial_key,
        label="📸 Capture DPI",
        on_change=_on_dpi_change,
    )


def _build_record_include_bgd_control(w: MoleculeViewerWidget) -> Any:
    """Build include background in capture checkbox."""

    def _on_bgd_change(val: bool) -> None:
        w.record_include_bgd = bool(val)

    return mo.ui.checkbox(
        value=bool(getattr(w, "record_include_bgd", False)),
        label="🖼️ Include Background in Capture",
        on_change=_on_bgd_change,
    )


def _build_record_include_ui_control(w: MoleculeViewerWidget) -> Any:
    """Build include UI in capture checkbox."""

    def _on_ui_change(val: bool) -> None:
        w.record_include_ui = bool(val)

    return mo.ui.checkbox(
        value=bool(getattr(w, "record_include_ui", False)),
        label="🎛️ Include UI in Capture",
        on_change=_on_ui_change,
    )


CONTROL_BUILDERS = {
    # Appearance
    "background": _build_background_control,
    "background_color": _build_background_control,
    "style": _build_style_control,
    "projection": _build_projection_control,
    "width": _build_width_control,
    "height": _build_height_control,
    "viewer_outline": _build_outline_control,
    # Motion
    "spin": _build_spin_control,
    "spin_speed": _build_spin_speed_control,
    "spin_axis": _build_spin_axis_control,
    "multi_traj": _build_multi_traj_control,
    "traj_fps": _build_fps_control,
    "trajectory_slider": _build_trajectory_slider_control,
    # Display & Tools
    "draw_outlines": _build_outlines_control,
    "draw_labels": _build_labels_control,
    "show_axes": _build_axes_control,
    "fog": _build_fog_control,
    "fog_strength": _build_fog_strength_control,
    "clip_distance": _build_clip_distance_control,
    "structure_transparency": _build_transparency_control,
    "measuring_tool": _build_measuring_control,
    "show_help": _build_help_control,
    # Vectors
    "vector_width": _build_vector_width_control,
    "vector_outline": _build_vector_outline_control,
    "vector_color": _build_vector_color_control,
    # Capture & Export
    "recording_tools": _build_recording_tools_control,
    "dpi": _build_dpi_control,
    "record_include_bgd": _build_record_include_bgd_control,
    "record_include_ui": _build_record_include_ui_control,
}


def _group_controls_by_category(elements: dict[str, Any]) -> dict[str, list[Any]]:
    """Categorize controls into logical sections."""
    app_keys = [
        "background",
        "background_color",
        "style",
        "projection",
        "width",
        "height",
        "viewer_outline",
    ]
    mot_keys = [
        "spin",
        "spin_speed",
        "spin_axis",
        "multi_traj",
        "traj_fps",
        "trajectory_slider",
    ]
    disp_keys = [
        "draw_outlines",
        "draw_labels",
        "show_axes",
        "fog",
        "fog_strength",
        "clip_distance",
        "structure_transparency",
        "measuring_tool",
        "show_help",
    ]
    vec_keys = ["vector_width", "vector_outline", "vector_color"]
    rec_keys = [
        "recording_tools",
        "dpi",
        "record_include_bgd",
        "record_include_ui",
    ]

    return {
        "🎨 Appearance": [
            elements[k]
            for k in app_keys
            if k in elements and not (k == "background_color" and "background" in elements)
        ],
        "🔄 Motion": [elements[k] for k in mot_keys if k in elements],
        "✨ Display & Tools": [elements[k] for k in disp_keys if k in elements],
        "🏹 Vectors": [elements[k] for k in vec_keys if k in elements],
        "🎥 Capture & Export": [elements[k] for k in rec_keys if k in elements],
    }


def _build_grid_layout(cat_dict: dict[str, list[Any]]) -> Any:
    """Build clean multi-column card layout."""
    cols = []
    for title, items in cat_dict.items():
        if items:
            cols.append(mo.vstack([mo.md(f"**{title}**"), *items], gap=0.5))
    return mo.hstack(cols, justify="space-around", gap=1.0)


def _build_layout(
    elements: dict[str, Any],
    selected_names: list[str],
    layout_name: str,
) -> Any:
    """Compose the marimo layout container from UI elements."""
    cat_dict = _group_controls_by_category(elements)
    all_items = [elements[k] for k in selected_names if k in elements]

    if layout_name in ("grid", "compact"):
        return _build_grid_layout(cat_dict)

    if layout_name == "accordion":
        sections = {title: mo.vstack(items, gap=0.5) for title, items in cat_dict.items() if items}
        return mo.accordion(sections)

    if layout_name == "tabs":
        tabs_dict = {title: mo.vstack(items, gap=0.5) for title, items in cat_dict.items() if items}
        return mo.ui.tabs(tabs_dict)

    if layout_name == "horizontal":
        return mo.hstack(all_items, justify="start", gap=0.75)

    if layout_name == "vertical":
        return mo.vstack(all_items, gap=0.5)

    return _build_grid_layout(cat_dict)


def _resolve_available_controls(w: MoleculeViewerWidget) -> list[str]:
    """Determine available control names for a viewer widget."""
    has_vectors = False
    if isinstance(w.data, list):
        has_vectors = any(bool(f.get("vectors")) for f in w.data if isinstance(f, dict))
    elif isinstance(w.data, dict):
        has_vectors = bool(w.data.get("vectors"))

    controls_list = [
        "background",
        "style",
        "projection",
        "width",
        "height",
        "viewer_outline",
        "spin",
        "spin_speed",
        "spin_axis",
        "draw_outlines",
        "draw_labels",
        "show_axes",
        "fog",
        "fog_strength",
        "clip_distance",
        "structure_transparency",
        "measuring_tool",
        "show_help",
        "recording_tools",
        "dpi",
        "record_include_bgd",
        "record_include_ui",
    ]
    if isinstance(w.data, list) and len(w.data) > 1:
        controls_list.extend(["multi_traj", "traj_fps", "trajectory_slider"])
    if has_vectors:
        controls_list.extend(["vector_width", "vector_outline", "vector_color"])
    return controls_list


def _filter_selected_controls(
    available: list[str],
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[str]:
    """Filter controls by include and exclude lists."""
    selected = list(available)
    if include is not None:
        selected = [name for name in selected if name in include]
    if exclude is not None:
        selected = [name for name in selected if name not in exclude]
    return selected


def create_controls(
    viewer: MoleculeViewerWidget | Any,
    layout: str = "grid",
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> MoleculeViewerControls:
    """
    Create a pre-wired interactive marimo control panel for a MoleculeViewerWidget.

    The returned controls panel is pre-configured with event callbacks (`on_change`) that mutate the
    underlying viewer widget's traitlets in real time. Because controls update widget traits directly
    over WebSockets/Comms, modifying settings (such as background color, style, or spin) updates the 3D
    scene immediately without re-executing notebook cells or resetting camera orientation and zoom.

    Parameters
    ----------
    viewer : MoleculeViewerWidget or marimo.ui.anywidget
        The viewer instance returned by `view_structure`, `view_ase`, `view_pymatgen`, or `view_cspy`.
    layout : str, optional
        Layout style for the control panel:
        - `'grid'` (default): Multi-column grouped card layout (Appearance, Motion, Display & Tools, Vectors, Capture).
        - `'accordion'`: Collapsible sections using `mo.accordion`.
        - `'tabs'`: Tabbed category layout using `mo.ui.tabs`.
        - `'vertical'`: Compact vertical stack.
        - `'horizontal'`: Inline horizontal row.
    include : list of str, optional
        List of control names to include. If None, all available controls are included.
    exclude : list of str, optional
        List of control names to exclude.

    Returns
    -------
    MoleculeViewerControls
        A displayable marimo UI container holding all pre-wired controls, with methods `to_dict()`,
        `to_toml()`, and `save_toml(path)` for saving and reusing configurations.

    Examples
    --------
    ```python
    import marimo as mo
    from ase.build import molecule
    from marimol import view_ase

    # In Cell 1:
    mol = molecule("C6H6")
    viewer = view_ase(mol)
    viewer

    # In Cell 2: Display pre-wired controls (updates viewer without cell re-run)
    controls = viewer.controls()
    controls

    # In Cell 3: Extract current configuration as a TOML string or dict (reactively updates!)
    toml_config = controls.to_toml()
    config_dict = controls.to_dict()
    ```
    *(added in v0.4.0)*
    """
    w = _extract_widget(viewer)

    available_controls = _resolve_available_controls(w)
    selected_names = _filter_selected_controls(available_controls, include, exclude)

    elements: dict[str, Any] = {}
    for name in selected_names:
        builder = CONTROL_BUILDERS.get(name)
        if builder is not None:
            elements[name] = builder(w)

    layout_lower = layout.lower().strip()
    root_layout = _build_layout(elements, selected_names, layout_lower)

    return MoleculeViewerControls(
        widget=w,
        elements=elements,
        layout=root_layout,
        layout_name=layout_lower,
    )


# Alias
controls = create_controls
