import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from ase.build import molecule

    from marimol import view_ase

    return mo, molecule, view_ase


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 🔬 Interactive Molecule Visualizer

    This example demonstrates 3D molecular visualization with **marimol**, real-time style switching,
    and **two-way reactivity** between 3D atom selections and downstream notebook cells.
    """)
    return


@app.cell
def _(mo):
    # UI Controls for interactive customization
    molecule_select = mo.ui.dropdown(
        options={
            "Benzene (C6H6)": "C6H6",
            "Pyridine (C5H5N)": "C5H5N",
            "Furan (C4H4O)": "C4H4O",
            "Pyrrole (C4H4NH)": "C4H4NH",
            "Ethanol (CH3CH2OH)": "CH3CH2OH",
            "Acetone (CH3COCH3)": "CH3COCH3",
        },
        value="Benzene (C6H6)",
        label="🧬 Molecule:",
    )

    style_select = mo.ui.dropdown(
        options=["ball-and-stick", "vdw", "wireframe"],
        value="ball-and-stick",
        label="🎨 Style:",
    )

    theme_select = mo.ui.dropdown(
        options={
            "Slate Dark (#0f172a)": "#0f172a",
            "Clean White (#ffffff)": "#ffffff",
            "Midnight Black (#000000)": "#000000",
            "Charcoal (#1e1e1e)": "#1e1e1e",
        },
        value="Slate Dark (#0f172a)",
        label="🖼️ Background:",
    )

    spin_toggle = mo.ui.checkbox(value=True, label="🔄 Auto-spin")
    spin_speed_slider = mo.ui.slider(start=-5.0, stop=5.0, step=0.5, value=1.5, label="⚡ Speed:")
    outlines_toggle = mo.ui.checkbox(value=True, label="✏️ Cel-shaded Outlines")
    measure_toggle = mo.ui.checkbox(value=True, label="📏 Measurement Tool")
    axes_toggle = mo.ui.checkbox(value=True, label="🧭 Show Axes")
    record_toggle = mo.ui.checkbox(value=True, label="🎥 Recording Tools")

    mo.hstack(
        [
            mo.vstack([molecule_select, style_select, theme_select]),
            mo.vstack([spin_toggle, spin_speed_slider, outlines_toggle]),
            mo.vstack([measure_toggle, axes_toggle, record_toggle]),
        ],
        justify="space-around",
    )
    return (
        axes_toggle,
        measure_toggle,
        molecule_select,
        outlines_toggle,
        record_toggle,
        spin_speed_slider,
        spin_toggle,
        style_select,
        theme_select,
    )


@app.cell
def _(
    axes_toggle,
    measure_toggle,
    molecule,
    molecule_select,
    outlines_toggle,
    record_toggle,
    spin_speed_slider,
    spin_toggle,
    style_select,
    theme_select,
    view_ase,
):
    mol = molecule(molecule_select.value)

    viewer = view_ase(
        mol,
        style=style_select.value,
        background_color=theme_select.value,
        spin=spin_toggle.value,
        spin_speed=spin_speed_slider.value,
        draw_outlines=outlines_toggle.value,
        measuring_tool=measure_toggle.value,
        show_axes=axes_toggle.value,
        recording_tools=record_toggle.value,
        record_include_bgd=True,
        record_include_ui=True,
        viewer_outline="1px solid #334155" if theme_select.value != "#ffffff" else "1px solid #e2e8f0",
        height="450px",
    )

    viewer
    return mol, viewer


@app.cell(hide_code=True)
def _(mo, mol, viewer):
    # Reactive inspection panel updated whenever the user clicks an atom
    selected = viewer.selected_atoms

    if not selected:
        info_content = mo.md(
            "💡 *Click on any atom in the 3D viewer above (or <kbd>Shift</kbd>+Click multiple atoms) to inspect details in real-time.*"
        )
    else:
        symbols = mol.get_chemical_symbols()
        positions = mol.get_positions()
        rows = []
        for idx in selected:
            if idx < len(symbols):
                pos = positions[idx]
                rows.append(
                    {
                        "Index": idx,
                        "Element": symbols[idx],
                        "X (Å)": f"{pos[0]:.4f}",
                        "Y (Å)": f"{pos[1]:.4f}",
                        "Z (Å)": f"{pos[2]:.4f}",
                    }
                )
        info_content = mo.vstack(
            [
                mo.md(f"### Selected Atoms ({len(selected)})"),
                mo.ui.table(rows),
            ]
        )

    mo.callout(info_content, kind="info")
    return


if __name__ == "__main__":
    app.run()
