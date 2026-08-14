from marimol import MoleculeViewerWidget, view_structure


def test_widget_selection_defaults():
    data = {
        "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "species": ["C", "O"],
    }
    ui_widget = view_structure(data)
    inner_widget = ui_widget.widget
    assert isinstance(inner_widget, MoleculeViewerWidget)
    assert inner_widget.selected_atoms == []


def test_widget_selection_mutation():
    widget = MoleculeViewerWidget(
        data=[
            {
                "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
                "species": ["C", "H", "H"],
            }
        ],
        selected_atoms=[0, 2],
    )
    assert widget.selected_atoms == [0, 2]

    # Test updating selected_atoms
    widget.selected_atoms = [1]
    assert widget.selected_atoms == [1]

    # Test clearing selected_atoms
    widget.selected_atoms = []
    assert widget.selected_atoms == []
