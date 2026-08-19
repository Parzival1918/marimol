from marimol import (
    MoleculeViewerControls,
    MoleculeViewerWidget,
    controls,
    create_controls,
    dict_to_toml,
    get_viewer_config,
    parse_toml_config,
    view_structure,
)
from marimol.utils import ATOMIC_RADII, VDW_RADII


def test_create_controls_basic():
    data = {
        "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "species": ["C", "O"],
    }
    ui_widget = view_structure(data)

    # Call .controls() on the returned marimo UI element
    panel = ui_widget.controls()
    assert isinstance(panel, MoleculeViewerControls)
    assert panel.widget is ui_widget.widget
    assert "background" in panel
    assert "style" in panel
    assert "spin" in panel
    assert "spin_speed" in panel
    assert "spin_axis" in panel
    assert "draw_outlines" in panel
    assert "draw_labels" in panel
    assert "show_axes" in panel
    assert "fog" in panel
    assert "fog_strength" in panel
    assert "clip_distance" in panel
    assert "structure_transparency" in panel
    assert "measuring_tool" in panel
    assert "show_help" in panel
    assert "projection" in panel
    assert "width" in panel
    assert "height" in panel
    assert "viewer_outline" in panel
    assert "recording_tools" in panel
    assert "dpi" in panel
    assert "record_include_bgd" in panel
    assert "record_include_ui" in panel

    # Trajectory controls not present for single frame
    assert "multi_traj" not in panel
    assert "traj_fps" not in panel
    assert "trajectory_slider" not in panel

    # Test mime and repr
    mime = panel._mime_()
    assert isinstance(mime, tuple)
    assert mime[0] == "text/html"
    assert panel._repr_html_() != ""
    assert isinstance(panel._repr_markdown_(), str)


def test_create_controls_layouts():
    data = {
        "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "species": ["C", "O"],
    }
    ui_widget = view_structure(data)

    for layout_name in [
        "grid",
        "compact",
        "accordion",
        "tabs",
        "vertical",
        "horizontal",
        "unknown",
    ]:
        panel = create_controls(ui_widget, layout=layout_name)
        assert isinstance(panel, MoleculeViewerControls)
        assert panel.layout is not None


def test_create_controls_include_exclude():
    data = {
        "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "species": ["C", "O"],
    }
    widget = MoleculeViewerWidget(data=[data])

    panel_inc = controls(widget, include=["background", "style"])
    assert len(panel_inc) == 2
    assert "background" in panel_inc
    assert "style" in panel_inc
    assert "spin" not in panel_inc

    panel_exc = controls(widget, exclude=["background", "style"])
    assert "background" not in panel_exc
    assert "style" not in panel_exc
    assert "spin" in panel_exc


def test_create_controls_trajectory_and_vectors():
    frames = [
        {
            "positions": [[0.0, 0.0, 0.0]],
            "species": ["H"],
            "vectors": [{"origin": 0, "direction": [1, 0, 0]}],
        },
        {
            "positions": [[0.1, 0.0, 0.0]],
            "species": ["H"],
            "vectors": [{"origin": 0, "direction": [0, 1, 0]}],
        },
    ]
    ui_widget = view_structure(frames)
    panel = ui_widget.controls()
    assert "multi_traj" in panel
    assert "traj_fps" in panel
    assert "trajectory_slider" in panel
    assert "vector_width" in panel
    assert "vector_outline" in panel
    assert "vector_color" in panel


def test_controls_callbacks_mutate_widget():
    data = {
        "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "species": ["C", "O"],
        "vectors": [{"origin": 0, "direction": [1, 0, 0]}],
    }
    ui_widget = view_structure(data)
    inner_widget = ui_widget.widget
    panel = ui_widget.controls()

    # 1. Background
    panel.background._on_change("#000000")
    assert inner_widget.background_color == "#000000"

    # 2. Style
    panel.style._on_change("vdw")
    assert inner_widget.style["use_vdw_radii"] is True
    assert inner_widget.radius_map == VDW_RADII

    panel.style._on_change("ball-and-stick")
    assert inner_widget.style["use_vdw_radii"] is False
    assert inner_widget.radius_map == ATOMIC_RADII

    # 3. Projection
    panel.projection._on_change("perspective")
    assert inner_widget.projection == "perspective"

    # 4. Width & Height & Outline
    panel.width._on_change("800px")
    assert inner_widget.width == "800px"

    panel.height._on_change("500px")
    assert inner_widget.height == "500px"

    panel.viewer_outline._on_change("1px solid #334155")
    assert inner_widget.viewer_outline == "1px solid #334155"

    # 5. Spin & Spin Speed & Axis
    panel.spin._on_change(True)
    assert inner_widget.spin is True

    panel.spin_speed._on_change(3.5)
    assert inner_widget.spin_speed == 3.5

    panel.spin_axis._on_change([1.0, 0.0, 0.0])
    assert inner_widget.spin_axis == [1.0, 0.0, 0.0]

    # 6. Outlines, Labels, Axes
    panel.draw_outlines._on_change(True)
    assert inner_widget.draw_outlines is True

    panel.draw_labels._on_change(True)
    assert inner_widget.draw_labels is True

    panel.show_axes._on_change(True)
    assert inner_widget.show_axes is True

    # 7. Fog & Fog Strength & Clip Distance
    panel.fog._on_change(True)
    assert inner_widget.fog is True

    panel.fog_strength._on_change(0.8)
    assert inner_widget.fog_strength == 0.8

    panel.clip_distance._on_change(12.5)
    assert inner_widget.clip_distance == 12.5

    # 8. Transparency & Measuring & Help
    panel.structure_transparency._on_change(0.4)
    assert inner_widget.structure_transparency == 0.4

    panel.measuring_tool._on_change(True)
    assert inner_widget.measuring_tool is True

    panel.show_help._on_change(False)
    assert inner_widget.show_help is False

    # 9. Vectors
    panel.vector_width._on_change(0.12)
    assert inner_widget.vector_width == 0.12

    panel.vector_outline._on_change("white")
    assert inner_widget.vector_outline == "white"

    panel.vector_color._on_change("yellow")
    assert inner_widget.vector_color == "#ffff00"

    # 10. Recording
    panel.recording_tools._on_change(True)
    assert inner_widget.recording_tools is True

    panel.dpi._on_change(300)
    assert inner_widget.dpi == 300

    panel.record_include_bgd._on_change(True)
    assert inner_widget.record_include_bgd is True

    panel.record_include_ui._on_change(True)
    assert inner_widget.record_include_ui is True


def test_controls_trajectory_callbacks():
    frames = [
        {"positions": [[0.0, 0.0, 0.0]], "species": ["H"]},
        {"positions": [[0.1, 0.0, 0.0]], "species": ["H"]},
    ]
    ui_widget = view_structure(frames)
    inner_widget = ui_widget.widget
    panel = ui_widget.controls()

    panel.multi_traj._on_change(False)
    assert inner_widget.multi_traj is False

    panel.traj_fps._on_change(24.0)
    assert inner_widget.traj_fps == 24.0

    panel.trajectory_slider._on_change(True)
    assert inner_widget.trajectory_slider is True


def test_widget_helper_methods():
    data = {
        "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "species": ["C", "O"],
    }
    widget = MoleculeViewerWidget(data=[data])

    widget.set_background_color("black")
    assert widget.background_color == "#000000"

    widget.set_style("wireframe")
    assert widget.style["bond_radius"] == 0.05
    assert widget.radius_map == ATOMIC_RADII

    widget.set_spin(True, speed=-4.0, axis=(1.0, 0.0, 0.0))
    assert widget.spin is True
    assert widget.spin_speed == -4.0
    assert widget.spin_axis == [1.0, 0.0, 0.0]


def test_config_extraction_and_toml_roundtrip(tmp_path):
    data = {
        "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "species": ["C", "O"],
    }
    ui_widget = view_structure(data)
    inner_widget = ui_widget.widget
    panel = ui_widget.controls()

    # Modify some settings
    inner_widget.background_color = "#0f172a"
    inner_widget.show_axes = True
    inner_widget.draw_outlines = True
    inner_widget.spin = True
    inner_widget.spin_speed = 1.5
    inner_widget.spin_axis = [0.0, 1.0, 0.0]
    inner_widget.structure_transparency = 0.25

    # 1. to_dict()
    cfg_dict = panel.to_dict()
    assert isinstance(cfg_dict, dict)
    assert cfg_dict["background_color"] == "#0f172a"
    assert cfg_dict["show_axes"] is True
    assert cfg_dict["draw_outlines"] is True
    assert cfg_dict["spin"] is True
    assert cfg_dict["spin_speed"] == 1.5
    assert cfg_dict["structure_transparency"] == 0.25

    # Widget to_dict and get_config
    assert inner_widget.to_dict() == cfg_dict
    assert inner_widget.get_config() == cfg_dict
    assert get_viewer_config(inner_widget) == cfg_dict

    # 2. to_toml()
    toml_str = panel.to_toml()
    assert isinstance(toml_str, str)
    assert 'background_color = "#0f172a"' in toml_str
    assert "show_axes = true" in toml_str
    assert "draw_outlines = true" in toml_str
    assert "spin = true" in toml_str
    assert "spin_speed = 1.5" in toml_str

    # Roundtrip with parse_toml_config
    parsed = parse_toml_config(toml_str)
    for k, v in cfg_dict.items():
        assert parsed[k] == v

    # 3. save_toml / save_config
    file_path = tmp_path / "custom_config.toml"
    panel.save_toml(file_path)
    assert file_path.exists()
    assert parse_toml_config(file_path)["background_color"] == "#0f172a"

    file_path2 = tmp_path / "widget_config.toml"
    inner_widget.save_config(file_path2)
    assert file_path2.exists()
    assert parse_toml_config(file_path2)["show_axes"] is True


def test_controls_reactive_toml_update():
    data = {
        "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "species": ["C", "O"],
    }
    ui_widget = view_structure(data)
    panel = ui_widget.controls()

    # Initial TOML
    initial_toml = panel.to_toml()
    assert 'background_color = "#ffffff"' in initial_toml
    assert "spin = false" in initial_toml

    # Change background through control
    panel.background._on_change("#0f172a")
    updated_toml_1 = panel.to_toml()
    assert 'background_color = "#0f172a"' in updated_toml_1

    # Change spin through control
    panel.spin._on_change(True)
    panel.spin_speed._on_change(5.0)
    updated_toml_2 = panel.to_toml()
    assert "spin = true" in updated_toml_2
    assert "spin_speed = 5.0" in updated_toml_2
    assert panel.config["spin"] is True
    assert panel.config["spin_speed"] == 5.0


def test_dict_to_toml():
    cfg = {
        "style": "ball-and-stick",
        "background_color": "#ffffff",
        "spin": False,
        "spin_speed": 2.0,
        "spin_axis": [0.0, 1.0, 0.0],
        "custom_table": {"key1": "val1", "key2": 42, "key3": True},
    }
    toml_out = dict_to_toml(cfg)
    parsed = parse_toml_config(toml_out)
    assert parsed["style"] == "ball-and-stick"
    assert parsed["spin_axis"] == [0.0, 1.0, 0.0]
    assert parsed["custom_table"]["key2"] == 42
