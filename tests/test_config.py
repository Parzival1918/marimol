import pytest

from marimol import MoleculeViewerWidget, parse_toml_config, view_structure


@pytest.fixture
def methane_dict():
    return {
        "positions": [
            [0.0, 0.0, 0.0],
            [0.6291, 0.6291, 0.6291],
            [-0.6291, -0.6291, 0.6291],
            [-0.6291, 0.6291, -0.6291],
            [0.6291, -0.6291, -0.6291],
        ],
        "species": ["C", "H", "H", "H", "H"],
    }


def test_parse_toml_config_dict():
    cfg = {"style": "wireframe", "spin": True, "dpi": 300}
    res = parse_toml_config(cfg)
    assert res == cfg
    assert res is not cfg  # should be a new dict copy


def test_parse_toml_config_string():
    toml_str = """
    style = "wireframe"
    background_color = "black"
    show_axes = true
    spin = true
    spin_speed = 4.5
    dpi = 300
    """
    res = parse_toml_config(toml_str)
    assert res["style"] == "wireframe"
    assert res["background_color"] == "black"
    assert res["show_axes"] is True
    assert res["spin"] is True
    assert res["spin_speed"] == 4.5
    assert res["dpi"] == 300


def test_parse_toml_config_pathlike(tmp_path):
    toml_file = tmp_path / "test_config.toml"
    toml_file.write_text("""
    style = "vdw"
    background_color = "cyan"
    draw_outlines = true
    measuring_tool = true
    """)

    # Test with Path object
    res_path = parse_toml_config(toml_file)
    assert res_path["style"] == "vdw"
    assert res_path["background_color"] == "cyan"
    assert res_path["draw_outlines"] is True
    assert res_path["measuring_tool"] is True

    # Test with str path
    res_str = parse_toml_config(str(toml_file))
    assert res_str["style"] == "vdw"
    assert res_str["background_color"] == "cyan"


def test_parse_toml_config_invalid_type():
    with pytest.raises(TypeError, match="Expected dict, str, or os.PathLike"):
        parse_toml_config(123)


def test_view_structure_with_dict_config(methane_dict):
    cfg = {
        "style": "wireframe",
        "background_color": "black",
        "show_axes": True,
        "spin": True,
        "spin_speed": 3.0,
        "recording_tools": True,
        "dpi": 400,
    }
    ui_widget = view_structure(methane_dict, config=cfg)
    inner = ui_widget.widget
    assert isinstance(inner, MoleculeViewerWidget)
    assert inner.background_color == "#000000"
    assert inner.show_axes is True
    assert inner.spin is True
    assert inner.spin_speed == 3.0
    assert inner.recording_tools is True
    assert inner.dpi == 400


def test_view_structure_with_toml_string_config(methane_dict):
    toml_str = """
    style = "wireframe"
    background_color = "red"
    draw_outlines = true
    fog = true
    fog_strength = 0.8
    """
    ui_widget = view_structure(methane_dict, config=toml_str)
    inner = ui_widget.widget
    assert isinstance(inner, MoleculeViewerWidget)
    assert inner.background_color == "#ff0000"
    assert inner.draw_outlines is True
    assert inner.fog is True
    assert inner.fog_strength == 0.8


def test_view_structure_with_toml_file_config(tmp_path, methane_dict):
    toml_file = tmp_path / "viewer_settings.toml"
    toml_file.write_text("""
    background_color = "gray"
    measuring_tool = true
    recording_tools = true
    record_include_bgd = true
    """)

    ui_widget = view_structure(methane_dict, config=toml_file)
    inner = ui_widget.widget
    assert isinstance(inner, MoleculeViewerWidget)
    assert inner.background_color == "#808080"
    assert inner.measuring_tool is True
    assert inner.recording_tools is True
    assert inner.record_include_bgd is True


def test_view_structure_argument_overwrite_config(methane_dict):
    cfg = {
        "background_color": "black",
        "spin": True,
        "spin_speed": 5.0,
        "show_axes": True,
        "recording_tools": True,
        "dpi": 600,
    }

    # Explicit arguments overwrite config values
    ui_widget = view_structure(
        methane_dict,
        config=cfg,
        background_color="white",  # overwrites black
        spin=False,  # overwrites True (falsy overwrite)
        dpi=150,  # overwrites 600
    )
    inner = ui_widget.widget
    assert isinstance(inner, MoleculeViewerWidget)
    assert inner.background_color == "#ffffff"
    assert inner.spin is False
    assert inner.spin_speed == 5.0  # untouched from config
    assert inner.show_axes is True  # untouched from config
    assert inner.recording_tools is True  # untouched from config
    assert inner.dpi == 150


def test_view_structure_nested_style_config(methane_dict):
    toml_str = """
    [style]
    bond_radius = 0.2
    use_vdw_radii = true
    """
    ui_widget = view_structure(methane_dict, config=toml_str)
    inner = ui_widget.widget
    assert isinstance(inner, MoleculeViewerWidget)
    assert inner.style == {"bond_radius": 0.2, "use_vdw_radii": True}


def test_view_structure_clip_distance(methane_dict):
    # Default clip_distance (disabled = 0.0)
    ui_default = view_structure(methane_dict)
    assert ui_default.widget.clip_distance == 0.0

    # Explicit clip_distance
    ui_custom = view_structure(methane_dict, clip_distance=5.0)
    assert ui_custom.widget.clip_distance == 5.0

    # From TOML config
    toml_str = """
    clip_distance = 12.5
    """
    ui_cfg = view_structure(methane_dict, config=toml_str)
    assert ui_cfg.widget.clip_distance == 12.5

    # Overwrite config (including explicitly disabling with 0.0)
    ui_over = view_structure(methane_dict, config=toml_str, clip_distance=0.0)
    assert ui_over.widget.clip_distance == 0.0
