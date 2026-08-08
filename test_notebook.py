import marimo

__generated_with = "0.8.2"
app = marimo.App()


@app.cell
def __():
    import marimo as mo
    from marimol import view_molecule, get_color, get_radius
    
    # A simple mock molecule (e.g. water)
    atoms = [
        {"position": [0.0, 0.0, 0.0], "color": get_color("O"), "radius": get_radius("O")},
        {"position": [0.75, 0.58, 0.0], "color": get_color("H"), "radius": get_radius("H")},
        {"position": [-0.75, 0.58, 0.0], "color": get_color("H"), "radius": get_radius("H")},
    ]
    
    viewer = view_molecule(atoms)
    return atoms, get_color, get_radius, mo, viewer


@app.cell
def __(viewer):
    viewer
    return


@app.cell
def __(mo, viewer):
    # This cell is reactive and will update whenever you click an atom!
    if viewer.selected_atom_index == -1:
        mo.md("### No atom selected. Click an atom to select it.")
    else:
        mo.md(f"### Selected Atom Index: **{viewer.selected_atom_index}**")
    return


if __name__ == "__main__":
    app.run()
