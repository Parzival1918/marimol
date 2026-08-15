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
    # 🎨 TOML Presets & Theme Configurations

    This example shows how to configure **marimol** using TOML presets via the `config` parameter,
    and how explicitly supplied arguments seamlessly override configuration settings.
    """)
    return


@app.cell
def _():
    # Define aesthetic presets as TOML strings
    PRESETS = {
        "🌌 Midnight Slate": """style = "ball-and-stick"
    background_color = "#0f172a"
    viewer_outline = "1px solid #334155"
    show_axes = true
    draw_outlines = true
    spin = true
    spin_speed = 1.5
    measuring_tool = true
    recording_tools = true
    record_include_bgd = true
    record_include_ui = true
        """,
        "📄 Clean Publication": """style = "ball-and-stick"
    background_color = "#ffffff"
    viewer_outline = "1px solid #e2e8f0"
    show_axes = true
    draw_outlines = true
    spin = false
    measuring_tool = true
    recording_tools = true
    record_include_bgd = false
        """,
        "📐 Blueprint Wireframe": """style = "wireframe"
    background_color = "#030712"
    viewer_outline = "1px solid #1e293b"
    show_axes = true
    draw_outlines = false
    spin = true
    spin_speed = 2.0
    measuring_tool = true
    recording_tools = true
    record_include_bgd = true
        """,
        "🧪 Van der Waals Space-filling": """style = "vdw"
    background_color = "#18181b"
    viewer_outline = "1px solid #27272a"
    show_axes = true
    draw_outlines = true
    spin = true
    spin_speed = 1.0
    measuring_tool = true
    recording_tools = true
    record_include_bgd = true
        """,
    }
    return (PRESETS,)


@app.cell
def _(PRESETS, mo):
    preset_dropdown = mo.ui.dropdown(
        options=list(PRESETS.keys()),
        value=list(PRESETS.keys())[0],
        label="🎭 Visual Preset:",
    )

    mol_dropdown = mo.ui.dropdown(
        options={
            "Benzene (C6H6)": "C6H6",
            "Pyridine (C5H5N)": "C5H5N",
            "Furan (C4H4O)": "C4H4O",
            "Ethanol (CH3CH2OH)": "CH3CH2OH",
        },
        value="Benzene (C6H6)",
        label="🧬 Molecule:",
    )

    override_spin = mo.ui.checkbox(value=False, label="⚡ Override Auto-spin (Force Fast Spin)")

    mo.hstack([preset_dropdown, mol_dropdown, override_spin], justify="space-between")
    return mol_dropdown, override_spin, preset_dropdown


@app.cell
def _(
    PRESETS,
    mol_dropdown,
    molecule,
    override_spin,
    preset_dropdown,
    view_ase,
):
    selected_toml = PRESETS[preset_dropdown.value]
    mol = molecule(mol_dropdown.value)

    # If the user toggled the override checkbox, pass explicit spin_speed to override the config
    kwargs = {}
    if override_spin.value:
        kwargs["spin"] = True
        kwargs["spin_speed"] = 5.0

    viewer = view_ase(
        mol,
        config=selected_toml,
        height="450px",
        **kwargs,
    )
    viewer
    return


@app.cell(hide_code=True)
def _(PRESETS, mo, preset_dropdown):
    # Display the TOML content for the selected preset
    mo.accordion(
        {
            f"📄 View TOML for {preset_dropdown.value}": mo.md(f"""
    ```toml
    {PRESETS[preset_dropdown.value].strip()}
    ```
    """)
        }
    )
    return


if __name__ == "__main__":
    app.run()
