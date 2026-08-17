import pytest

from marimol import MoleculeViewerWidget, process_vectors, view_structure


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


def test_process_vectors_atom_indices(methane_dict):
    methane_dict["vectors"] = [
        {"origin": 0, "end": 1},
        {"origin": 0, "end": 2, "color": "blue", "width": 0.12},
    ]

    res = process_vectors(methane_dict)
    assert len(res) == 2

    # Vector 1: atom 0 to atom 1
    assert res[0]["origin"] == [0.0, 0.0, 0.0]
    assert res[0]["end"] == [0.6291, 0.6291, 0.6291]
    assert pytest.approx(res[0]["length"], rel=1e-3) == 1.0896
    assert res[0]["width"] == 0.08
    assert res[0]["outline"] is False
    assert res[0]["color"] == "#ff0000"

    # Vector 2: atom 0 to atom 2 with custom color and width
    assert res[1]["origin"] == [0.0, 0.0, 0.0]
    assert res[1]["end"] == [-0.6291, -0.6291, 0.6291]
    assert res[1]["width"] == 0.12
    assert res[1]["color"] == "#0000ff"


def test_process_vectors_cartesian_coordinates():
    data = {
        "positions": [[0.0, 0.0, 0.0]],
        "species": ["C"],
        "vectors": [
            {"origin": [1.0, 2.0, 3.0], "end": [4.0, 6.0, 3.0]},
        ],
    }
    res = process_vectors(data)
    assert len(res) == 1
    assert res[0]["origin"] == [1.0, 2.0, 3.0]
    assert res[0]["end"] == [4.0, 6.0, 3.0]
    assert pytest.approx(res[0]["length"]) == 5.0
    assert pytest.approx(res[0]["direction"]) == [0.6, 0.8, 0.0]


def test_process_vectors_direction_and_length():
    data = {
        "positions": [[0.0, 0.0, 0.0]],
        "species": ["C"],
        "vectors": [
            {"origin": [1.0, 1.0, 1.0], "direction": [0.0, 0.0, 5.0], "length": 3.0},
        ],
    }
    res = process_vectors(data)
    assert len(res) == 1
    assert res[0]["origin"] == [1.0, 1.0, 1.0]
    assert pytest.approx(res[0]["direction"]) == [0.0, 0.0, 1.0]
    assert res[0]["length"] == 3.0
    assert pytest.approx(res[0]["end"]) == [1.0, 1.0, 4.0]


def test_process_vectors_direction_without_explicit_length():
    data = {
        "positions": [[0.0, 0.0, 0.0]],
        "species": ["C"],
        "vectors": [
            {"origin": [0.0, 0.0, 0.0], "direction": [3.0, 4.0, 0.0]},
        ],
    }
    res = process_vectors(data)
    assert len(res) == 1
    assert pytest.approx(res[0]["length"]) == 5.0
    assert pytest.approx(res[0]["direction"]) == [0.6, 0.8, 0.0]
    assert pytest.approx(res[0]["end"]) == [3.0, 4.0, 0.0]


def test_process_vectors_end_overrides_direction():
    # When both "end" and "direction" + "length" are provided, "end" value is used
    data = {
        "positions": [[0.0, 0.0, 0.0]],
        "species": ["C"],
        "vectors": [
            {
                "origin": [0.0, 0.0, 0.0],
                "end": [0.0, 0.0, 10.0],
                "direction": [1.0, 0.0, 0.0],
                "length": 2.0,
            }
        ],
    }
    res = process_vectors(data)
    assert len(res) == 1
    assert res[0]["end"] == [0.0, 0.0, 10.0]
    assert res[0]["length"] == 10.0
    assert pytest.approx(res[0]["direction"]) == [0.0, 0.0, 1.0]


def test_process_vectors_styling_precedence():
    data = {
        "positions": [[0.0, 0.0, 0.0]],
        "species": ["C"],
        "vector_width": 0.10,
        "vector_outline": True,
        "vector_color": "green",
        "vectors": [
            # Uses frame-level overrides
            {"origin": [0.0, 0.0, 0.0], "direction": [1.0, 0.0, 0.0], "length": 1.0},
            # Uses per-vector overrides
            {
                "origin": [0.0, 0.0, 0.0],
                "direction": [0.0, 1.0, 0.0],
                "length": 1.0,
                "width": 0.20,
                "outline": "2px solid red",
                "color": "#ffff00",
            },
        ],
    }
    res = process_vectors(data, default_width=0.05, default_outline=False, default_color="red")
    assert len(res) == 2

    # Vector 1: Inherits frame-level settings
    assert res[0]["width"] == 0.10
    assert res[0]["outline"] is True
    assert res[0]["color"] == "#00ff00"

    # Vector 2: Overrides frame-level with per-vector settings
    assert res[1]["width"] == 0.20
    assert res[1]["outline"] == "2px solid red"
    assert res[1]["color"] == "#ffff00"


def test_process_vectors_errors(methane_dict):
    # Origin out of range
    methane_dict["vectors"] = [{"origin": 10, "end": 0}]
    with pytest.raises(IndexError, match="origin atom index 10 is out of bounds"):
        process_vectors(methane_dict)

    # End out of range
    methane_dict["vectors"] = [{"origin": 0, "end": 10}]
    with pytest.raises(IndexError, match="end atom index 10 is out of bounds"):
        process_vectors(methane_dict)

    # Invalid origin length
    methane_dict["vectors"] = [{"origin": [1.0, 2.0], "end": [0.0, 0.0, 0.0]}]
    with pytest.raises(ValueError, match="origin coordinate list must have length 3"):
        process_vectors(methane_dict)

    # Invalid end length
    methane_dict["vectors"] = [{"origin": [0.0, 0.0, 0.0], "end": [1.0, 2.0, 3.0, 4.0]}]
    with pytest.raises(ValueError, match="end coordinate list must have length 3"):
        process_vectors(methane_dict)

    # Missing origin key
    methane_dict["vectors"] = [{"end": 1}]
    with pytest.raises(ValueError, match="missing required 'origin' key"):
        process_vectors(methane_dict)

    # Missing end and direction
    methane_dict["vectors"] = [{"origin": 0}]
    with pytest.raises(ValueError, match="must specify either 'end'"):
        process_vectors(methane_dict)

    # Invalid vector entry type
    methane_dict["vectors"] = ["not-a-dict"]
    with pytest.raises(TypeError, match="must be a dictionary"):
        process_vectors(methane_dict)

    # Invalid origin type
    methane_dict["vectors"] = [{"origin": "atom0", "end": 1}]
    with pytest.raises(TypeError, match="origin must be an atom index"):
        process_vectors(methane_dict)


def test_view_structure_with_vectors(methane_dict):
    methane_dict["vectors"] = [
        {"origin": 0, "end": 1, "color": "cyan"},
        {"origin": [0.0, 0.0, 0.0], "direction": [0.0, 1.0, 0.0], "length": 2.0},
    ]

    ui_widget = view_structure(
        methane_dict,
        vector_width=0.10,
        vector_outline=True,
        vector_color="magenta",
    )
    inner = ui_widget.widget
    assert isinstance(inner, MoleculeViewerWidget)
    assert inner.vector_width == 0.10
    assert inner.vector_outline is True
    assert inner.vector_color == "#ff00ff"

    # Verify widget data vectors are converted to cartesian coordinates
    frame_data = inner.data[0]
    assert len(frame_data["vectors"]) == 2
    assert frame_data["vectors"][0]["origin"] == [0.0, 0.0, 0.0]
    assert frame_data["vectors"][0]["end"] == [0.6291, 0.6291, 0.6291]
    assert frame_data["vectors"][0]["color"] == "#00ffff"
    assert frame_data["vectors"][1]["color"] == "#ff00ff"


def test_view_structure_with_toml_config_vectors(methane_dict):
    toml_str = """
    vector_width = 0.14
    vector_outline = true
    vector_color = "yellow"
    """
    methane_dict["vectors"] = [{"origin": 0, "end": 1}]

    # 1. Using TOML config directly
    ui_widget = view_structure(methane_dict, config=toml_str)
    inner = ui_widget.widget
    assert inner.vector_width == 0.14
    assert inner.vector_outline is True
    assert inner.vector_color == "#ffff00"

    # 2. Overriding TOML config via explicit arguments
    ui_widget_override = view_structure(
        methane_dict,
        config=toml_str,
        vector_width=0.06,
        vector_color="blue",
    )
    inner_override = ui_widget_override.widget
    assert inner_override.vector_width == 0.06
    assert inner_override.vector_color == "#0000ff"
    assert inner_override.vector_outline is True  # preserved from config


def test_view_structure_trajectory_vectors(methane_dict):
    frame1 = dict(methane_dict)
    frame1["vectors"] = [{"origin": 0, "end": 1}]

    frame2 = dict(methane_dict)
    frame2["vectors"] = [{"origin": 0, "end": 2, "color": "orange"}]

    traj = [frame1, frame2]
    ui_widget = view_structure(traj)
    inner = ui_widget.widget

    assert len(inner.data) == 2
    assert inner.data[0]["vectors"][0]["end"] == [0.6291, 0.6291, 0.6291]
    assert inner.data[1]["vectors"][0]["end"] == [-0.6291, -0.6291, 0.6291]
    assert inner.data[1]["vectors"][0]["color"] == "orange"


def test_view_structure_vector_precedence_retains_reactivity(methane_dict):
    raw_vector = {"origin": 0, "end": 1}
    methane_dict["vectors"] = [raw_vector]

    # Call view_structure with specific vector_width
    ui_widget = view_structure(methane_dict, vector_width=0.15)
    inner = ui_widget.widget
    assert inner.vector_width == 0.15

    # Check that processed vector dictionary does not have baked-in width/outline overrides
    assert "width" not in methane_dict["vectors"][0]
    assert "outline" not in methane_dict["vectors"][0]

    # Calling again with a different vector_width works dynamically
    ui_widget2 = view_structure(methane_dict, vector_width=0.04)
    inner2 = ui_widget2.widget
    assert inner2.vector_width == 0.04


def test_view_structure_structure_transparency(methane_dict):
    ui_widget = view_structure(methane_dict, structure_transparency=0.45)
    inner = ui_widget.widget
    assert inner.structure_transparency == 0.45

    # Default is 0.0
    ui_default = view_structure(methane_dict)
    assert ui_default.widget.structure_transparency == 0.0
