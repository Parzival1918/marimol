import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from ase.build import bulk

    from marimol import view_ase

    return bulk, mo, view_ase


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 💎 Periodic Crystal Structures & Crystallographic Data

    This example demonstrates visualizing periodic lattices, unit cell wireframes,
    depth cueing fog, and automatic extraction of crystallographic metrics (density, volume, lattice vectors).
    """)
    return


@app.cell
def _(mo):
    crystal_dropdown = mo.ui.dropdown(
        options={
            "Silicon (Diamond Cubic)": ("Si", "diamond", 5.43),
            "Rock Salt (NaCl)": ("NaCl", "rocksalt", 5.64),
            "Copper (FCC)": ("Cu", "fcc", 3.61),
            "Gold (FCC)": ("Au", "fcc", 4.08),
            "Iron (BCC)": ("Fe", "bcc", 2.87),
        },
        value="Silicon (Diamond Cubic)",
        label="💠 Crystal:",
    )

    style_dropdown = mo.ui.dropdown(
        options=["ball-and-stick", "vdw", "wireframe"],
        value="ball-and-stick",
        label="🎨 Style:",
    )

    fog_toggle = mo.ui.checkbox(value=True, label="🌫️ Distance Fog")
    fog_slider = mo.ui.slider(start=0.1, stop=1.0, step=0.1, value=0.6, label="Fog Strength:")
    spin_toggle = mo.ui.checkbox(value=True, label="🔄 Auto-spin")
    spin_speed = mo.ui.slider(start=-4.0, stop=4.0, step=0.5, value=1.0, label="Spin Speed:")

    mo.hstack(
        [
            mo.vstack([crystal_dropdown, style_dropdown]),
            mo.vstack([fog_toggle, fog_slider]),
            mo.vstack([spin_toggle, spin_speed]),
        ],
        justify="space-around",
    )
    return (
        crystal_dropdown,
        fog_slider,
        fog_toggle,
        spin_speed,
        spin_toggle,
        style_dropdown,
    )


@app.cell
def _(
    bulk,
    crystal_dropdown,
    fog_slider,
    fog_toggle,
    spin_speed,
    spin_toggle,
    style_dropdown,
    view_ase,
):
    elem, struct_type, lattice_a = crystal_dropdown.value
    atoms = bulk(elem, struct_type, a=lattice_a)

    viewer = view_ase(
        atoms,
        style=style_dropdown.value,
        background_color="#0f172a",
        show_axes=True,
        compute_extra_data=True,
        fog=fog_toggle.value,
        fog_strength=fog_slider.value,
        spin=spin_toggle.value,
        spin_speed=spin_speed.value,
        draw_outlines=True,
        measuring_tool=True,
        recording_tools=True,
        record_include_bgd=True,
        viewer_outline="1px solid #334155",
        height="450px",
    )
    viewer
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    > 💡 **Tip**: Click the **List icon (📋)** on the top-right toolbar inside the viewer to open the **Extra Data drawer** and view computed physical properties such as density ($\text{g/cm}^3$), unit cell volume ($\text{\AA}^3$), lattice constants ($a, b, c$), and cell angles ($\alpha, \beta, \gamma$).
    """)
    return


if __name__ == "__main__":
    app.run()
