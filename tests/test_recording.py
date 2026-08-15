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


def test_recording_tools_explicit_false(methane_dict):
    ui_widget = view_structure(methane_dict, recording_tools=False)
    inner = ui_widget.widget
    assert isinstance(inner, MoleculeViewerWidget)
    assert inner.recording_tools is False


def test_recording_tools_explicit_true(methane_dict):
    ui_widget = view_structure(methane_dict, recording_tools=True, dpi=600)
    inner = ui_widget.widget
    assert isinstance(inner, MoleculeViewerWidget)
    assert inner.recording_tools is True
    assert inner.dpi == 600


def test_widget_recording_tools_traitlet():
    widget = MoleculeViewerWidget()
    assert widget.recording_tools is False
    assert widget.dpi == 200
    widget.recording_tools = True
    assert widget.recording_tools is True
    widget.dpi = 150
    assert widget.dpi == 150
    widget.recording_tools = False
    assert widget.recording_tools is False


def test_recording_tools_trajectory(methane_dict):
    traj = [methane_dict, methane_dict]
    ui_widget = view_structure(traj, recording_tools=True, dpi=150)
    inner = ui_widget.widget
    assert isinstance(inner, MoleculeViewerWidget)
    assert inner.recording_tools is True
    assert inner.dpi == 150
