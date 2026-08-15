import pytest

from marimol import MoleculeViewerWidget, view_structure


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


def test_recording_tools_default(methane_dict):
    ui_widget = view_structure(methane_dict)
    inner = ui_widget.widget
    assert isinstance(inner, MoleculeViewerWidget)
    assert inner.recording_tools is False
    assert inner.dpi == 200
    assert inner.record_include_bgd is False
    assert inner.record_include_ui is False


def test_recording_tools_explicit_false(methane_dict):
    ui_widget = view_structure(methane_dict, recording_tools=False, record_include_bgd=False, record_include_ui=False)
    inner = ui_widget.widget
    assert isinstance(inner, MoleculeViewerWidget)
    assert inner.recording_tools is False
    assert inner.record_include_bgd is False
    assert inner.record_include_ui is False


def test_recording_tools_explicit_true(methane_dict):
    ui_widget = view_structure(
        methane_dict,
        recording_tools=True,
        dpi=600,
        record_include_bgd=True,
        record_include_ui=True,
    )
    inner = ui_widget.widget
    assert isinstance(inner, MoleculeViewerWidget)
    assert inner.recording_tools is True
    assert inner.dpi == 600
    assert inner.record_include_bgd is True
    assert inner.record_include_ui is True


def test_widget_recording_tools_traitlet():
    widget = MoleculeViewerWidget()
    assert widget.recording_tools is False
    assert widget.dpi == 200
    assert widget.record_include_bgd is False
    assert widget.record_include_ui is False

    widget.recording_tools = True
    assert widget.recording_tools is True
    widget.dpi = 150
    assert widget.dpi == 150
    widget.record_include_bgd = True
    assert widget.record_include_bgd is True
    widget.record_include_ui = True
    assert widget.record_include_ui is True

    widget.recording_tools = False
    assert widget.recording_tools is False
    widget.record_include_bgd = False
    assert widget.record_include_bgd is False
    widget.record_include_ui = False
    assert widget.record_include_ui is False


def test_recording_tools_trajectory(methane_dict):
    traj = [methane_dict, methane_dict]
    ui_widget = view_structure(
        traj,
        recording_tools=True,
        dpi=150,
        record_include_bgd=True,
        record_include_ui=True,
    )
    inner = ui_widget.widget
    assert isinstance(inner, MoleculeViewerWidget)
    assert inner.recording_tools is True
    assert inner.dpi == 150
    assert inner.record_include_bgd is True
    assert inner.record_include_ui is True
