import marimo

__generated_with = "0.23.16"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    from marimol import view_molecule, get_color, get_radius

    # A simple mock molecule (e.g. water)
    atoms = [
        {"position": [0.0, 0.0, 0.0], "color": get_color("O"), "radius": get_radius("O")},
        {"position": [0.75, 0.58, 0.0], "color": get_color("H"), "radius": get_radius("H")},
        {"position": [-0.75, 0.58, 0.0], "color": get_color("H"), "radius": get_radius("H")},
    ]

    # Example 3x3 unit cell matrix (simple cubic, side length 2.0 A)
    unit_cell = [
        [2.0, 0.0, 0.0],
        [0.0, 2.0, 0.0],
        [0.0, 0.0, 2.0]
    ]

    viewer = view_molecule(atoms, unit_cell=unit_cell, style="wireframe", show_axes=True)
    return mo, viewer


@app.cell
def _(mo, text, viewer):
    mo.vstack([viewer, text])
    return


@app.cell
def _(mo, viewer):
    # This cell is reactive and will update whenever you click an atom!
    if viewer.selected_atom_index == -1:
        text = mo.md("### No atom selected. Click an atom to select it.")
    else:
        text = mo.md(f"### Selected Atom Index: **{viewer.selected_atom_index}**")
    return (text,)


if __name__ == "__main__":
    app.run()
