from marimol import MoleculeViewerWidget, view_structure


def test_view_structure_show_help_default():
    data = {
        "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "species": ["C", "O"],
    }
    ui_widget = view_structure(data)
    inner_widget = ui_widget.widget
    assert isinstance(inner_widget, MoleculeViewerWidget)
    assert inner_widget.show_help is True


def test_view_structure_show_help_false():
    data = {
        "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "species": ["C", "O"],
    }
    ui_widget = view_structure(data, show_help=False)
    inner_widget = ui_widget.widget
    assert isinstance(inner_widget, MoleculeViewerWidget)
    assert inner_widget.show_help is False


def test_view_structure_show_help_true_explicit():
    data = {
        "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "species": ["C", "O"],
    }
    ui_widget = view_structure(data, show_help=True)
    inner_widget = ui_widget.widget
    assert isinstance(inner_widget, MoleculeViewerWidget)
    assert inner_widget.show_help is True


def test_widget_show_help_traitlet():
    widget = MoleculeViewerWidget(
        data=[
            {
                "positions": [[0.0, 0.0, 0.0]],
                "species": ["C"],
            }
        ]
    )
    assert widget.show_help is True

    widget.show_help = False
    assert widget.show_help is False

    widget.show_help = True
    assert widget.show_help is True


def test_view_structure_show_help_trajectory():
    frames = [
        {"positions": [[0.0, 0.0, 0.0]], "species": ["C"]},
        {"positions": [[1.0, 0.0, 0.0]], "species": ["C"]},
    ]
    ui_widget_1 = view_structure(frames, show_help=False)
    assert ui_widget_1.widget.show_help is False

    ui_widget_2 = view_structure(frames, show_help=True)
    assert ui_widget_2.widget.show_help is True
