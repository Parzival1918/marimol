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
    # 🎛️ Pre-wired Interactive Controls & Configuration Export

    When arguments inside a viewer cell change in marimo, the reactive cell re-runs, which creates a new 3D widget and resets the camera angle, zoom, and atom selections.

    With **`viewer.controls()`** *(introduced in v0.4.0)*, **marimol** provides a pre-wired interactive control panel that updates all viewer settings (background, render style, spin, projection, structure outlines, atom labels, fog, transparency, clipping, and recording tools) in real time via WebSockets **without re-running the viewer cell or resetting your camera viewpoint**.

    You can also extract the live configuration at any time as a **TOML string** (`panel.to_toml()`) or **dictionary** (`panel.to_dict()`) and reuse it across other viewers with the `config` parameter!
    """)
    return


@app.cell
def _(mo):
    mol_select = mo.ui.dropdown(
        options={
            "Benzene": "C6H6",
            "Ethanol": "CH3CH2OH",
            "Bicyclobutane": "bicyclobutane",
        },
        value="Benzene",
        label="🧬 Select Molecule:",
    )
    mol_select
    return (mol_select,)


@app.cell
def _(mol_select, molecule, view_ase):
    # Viewer created once per molecule selection
    mol = molecule(mol_select.value)
    viewer = view_ase(
        mol,
        background_color="#0f172a",
        style="ball-and-stick",
        draw_outlines=True,
        show_axes=True,
        measuring_tool=True,
        recording_tools=True,
        viewer_outline="1px solid #334155",
        height="450px",
    )
    viewer
    return mol, viewer


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ### 🎛️ Live Viewer Controls *(no camera reset!)*

    Try changing the **Background**, **Style**, **structure outlines**, **Fog**, **Projection**, or **Auto-spin** below.
    The 3D viewer updates **instantly in place** while preserving your camera rotation and zoom.
    """)
    return


@app.cell
def _(mo):
    layout_mode = mo.ui.radio(
        options=["grid", "accordion", "tabs"],
        value="grid",
        label="📐 Control Panel Layout Style:",
        inline=True,
    )
    layout_mode
    return (layout_mode,)


@app.cell
def _(layout_mode, viewer):
    # Generates pre-wired interactive controls with all configuration options
    panel = viewer.controls(layout=layout_mode.value)
    panel
    return (panel,)


@app.cell(hide_code=True)
def _(mo, panel):
    mo.accordion(
        {
            "💡 Custom Layout with Individual Controls": mo.vstack(
                [
                    mo.md(
                        "You can also embed individual pre-wired controls anywhere in your notebook layouts:"
                    ),
                    mo.hstack(
                        [
                            panel.background,
                            panel.style,
                            panel.spin,
                            panel.spin_speed,
                        ],
                        justify="center",
                        gap=1.0,
                    ),
                ],
                gap=0.5,
            )
        }
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ### 📄 Extract & Reuse Configuration

    Once you have customized the viewer to your preferred visual theme, you can export the configuration as a **TOML string** or **dictionary** and pass it directly to `config` in other viewers:
    """)
    return


@app.cell
def _(mo, panel):
    # Live extraction of current configuration
    current_toml = panel.to_toml()
    current_dict = panel.to_dict()
    mo.accordion(
        {
            "📋 Current Viewer Configuration (TOML)": mo.md(
                f"```toml\n{current_toml}\n```"
            ),
            "📋 Current Viewer Configuration (dict)": current_dict
        }
    )
    return


@app.cell(hide_code=True)
def _(mo, mol, viewer):
    selected = viewer.selected_atoms
    if not selected:
        info_content = mo.md(
            "💡 *Click on any atom in the 3D viewer above (or <kbd>Shift</kbd>+Click multiple atoms) to inspect details in real-time.*"
        )
    else:
        symbols = mol.get_chemical_symbols()
        positions = mol.get_positions()
        rows = [
            {
                "Index": idx,
                "Element": symbols[idx],
                "X (Å)": f"{positions[idx][0]:.4f}",
                "Y (Å)": f"{positions[idx][1]:.4f}",
                "Z (Å)": f"{positions[idx][2]:.4f}",
            }
            for idx in selected
            if idx < len(symbols)
        ]
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
