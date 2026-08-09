import marimo

__generated_with = "0.23.16"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    from marimol import view_molecule, get_color, get_radius

    import math

    # A simple mock molecule (e.g. water) animated over 30 frames
    frames_atoms = []
    for f in range(30):
        offset = math.sin(f / 30.0 * 2 * math.pi) * 0.5
        atoms = {
            "positions": [[0.0, offset, 0.0], [0.75, 0.58 + offset, 0.0], [-0.75, 0.58 + offset, 0.0]],
            "species": ["O", "H", "H"],
            "unit_cell": [
                [2.0, 0.0, 0.0],
                [0.0, 2.0, 0.0],
                [0.0, 0.0, 2.0]
            ],
            "labels": ["A", "B", "C"]
        }
        frames_atoms.append(atoms)

    viewer = view_molecule(frames_atoms, draw_labels=True, show_axes=True, projection="orthographic", fog=True, fog_strength=0.5, draw_outlines=True)
    return mo, viewer


@app.cell
def _(viewer):
    viewer.height = "400px"
    viewer.outline = True
    return


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
        text = mo.md(f"### Selected Atom Index: **{viewer.selected_atom_index}** in frame {viewer.current_frame}")
    return (text,)


@app.cell
def _():
    from ase.build import molecule
    from marimol.external import view_ase

    mol = molecule("CH4", vacuum=2)
    view_ase(mol, style="wireframe", projection="orthographic", draw_outlines=True, outline=True, draw_labels=True)
    return mol, view_ase


@app.cell
def _(view_ase):
    from ase.build import bulk

    crys = bulk('Cu', 'hcp', a=3.6)
    view_ase(crys, style="ball-and-stick", projection="orthographic")
    return (crys,)


@app.cell
def _(view_ase):
    from ase.build import nanotube

    tube = nanotube(6, 0, length=4)
    print(tube)
    view_ase(tube, style="vdw", projection="orthographic")
    return (tube,)


@app.cell
def _(crys, mol, tube, view_ase):
    view_ase([mol, crys, tube], style="ball-and-stick", projection="orthographic", fog=True, fog_strength=1, draw_outlines=True)
    return


if __name__ == "__main__":
    app.run()
