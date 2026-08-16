import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import re
    import marimo as mo
    from cspy import Crystal, Molecule
    from cspy.crystal.generate_crystal import CrystalGenerator

    from marimol import view_cspy

    return Crystal, CrystalGenerator, Molecule, mo, re, view_cspy


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 🔮 Crystal Structure Generation with mol-cspy & Custom Metadata

    This example demonstrates generating predicted molecular crystal structures with **mol-cspy**'s `CrystalGenerator`.
    You can paste any molecular **XYZ coordinate string** to load via `Molecule.from_xyz_string()`, specify any
    target **space groups** (numbers 1–230), and adjust the number of molecules in the **asymmetric unit ($Z'$)**.

    A custom **`extra_data` callable** attaches the space group number, symbol, and $Z'$ directly to each frame's
    metadata drawer in the interactive 3D viewer.
    """)
    return


@app.cell
def _(mo):
    DEFAULT_XYZ = """5
    methane
    C 2.629 2.629 2.629
    H 2.000 3.258 2.000
    H 3.258 3.258 3.258
    H 2.000 2.000 3.258
    H 3.258 2.000 2.000"""

    xyz_input = mo.ui.text_area(
        value=DEFAULT_XYZ,
        label="🧬 XYZ Molecular Data (paste XYZ string):",
        rows=7,
    )

    sg_input = mo.ui.text(
        value="2, 14",
        label="💠 Space Groups (numbers 1–230, comma/space separated):",
    )

    z_prime_slider = mo.ui.slider(
        start=1,
        stop=4,
        step=1,
        value=1,
        label="🔢 Asymmetric Unit Molecules (Z'):",
    )

    n_per_sg_slider = mo.ui.slider(
        start=1,
        stop=5,
        step=1,
        value=3,
        label="📦 Structures per Space Group:",
    )

    clip_distance_slider = mo.ui.slider(
        start=0.0,
        stop=30.0,
        step=0.5,
        value=0.0,
        label="✂️ Clip Distance (0 = disabled):",
    )

    style_dropdown = mo.ui.dropdown(
        options=["ball-and-stick", "vdw", "wireframe"],
        value="ball-and-stick",
        label="🎨 Style:",
    )

    mo.vstack(
        [
            xyz_input,
            mo.hstack([sg_input, z_prime_slider], justify="space-between"),
            mo.hstack([n_per_sg_slider, clip_distance_slider, style_dropdown], justify="space-between"),
        ]
    )
    return (
        clip_distance_slider,
        n_per_sg_slider,
        sg_input,
        style_dropdown,
        xyz_input,
        z_prime_slider,
    )


@app.cell
def _(
    Crystal,
    CrystalGenerator,
    Molecule,
    clip_distance_slider,
    mo,
    n_per_sg_slider,
    re,
    sg_input,
    style_dropdown,
    view_cspy,
    xyz_input,
    z_prime_slider,
):
    # 1. Parse molecule from user-provided XYZ string
    xyz_text = xyz_input.value.strip()
    parse_error = None
    try:
        lines = [line.strip() for line in xyz_text.splitlines() if line.strip()]
        if not lines:
            raise ValueError("XYZ data cannot be empty.")
        try:
            int(lines[0])
            formatted_xyz = "\n".join(lines)
        except ValueError:
            formatted_xyz = f"{len(lines)}\nmolecule\n" + "\n".join(lines)

        mol = Molecule.from_xyz_string(formatted_xyz)
        mol.guess_bonds()
    except Exception as err:
        parse_error = str(err)
        mol = None

    mo.stop(mol is None, mo.md(f"⚠️ **Error parsing XYZ data**: `{parse_error}`. Please check the XYZ format."))

    # 2. Parse space groups (validating range 1 to 230)
    raw_tokens = re.findall(r"([+-]?\d+)", sg_input.value)
    valid_space_groups = []
    invalid_tokens = []
    for token in raw_tokens:
        sg_num = int(token)
        if 1 <= sg_num <= 230:
            if sg_num not in valid_space_groups:
                valid_space_groups.append(sg_num)
        else:
            invalid_tokens.append(token)

    if not valid_space_groups:
        valid_space_groups = [2, 14]

    z_prime = z_prime_slider.value
    n_per_sg = n_per_sg_slider.value

    # 3. Generate candidate crystals for each selected space group
    crystals = []
    for sg in valid_space_groups:
        try:
            generator = CrystalGenerator([mol] * z_prime, space_group=sg)
            count = 0
            seed = 1
            while count != n_per_sg:
                candidate = generator.generate(seed)
                if candidate is not None:
                    crystals.append(candidate)
                    count += 1
                seed += 1
        except Exception as e:
            print(e)
            continue

    # 4. Define custom callable to extract space group and asymmetric unit count
    def extract_crystal_metadata(c: Crystal) -> dict:
        return {
            "space group": f"{c.space_group.international_tables_number} ({c.space_group.symbol})",
            "Z' (asym molecules)": len(c.asym_mols()),
        }

    # 5. Visualize the generated structures
    viewer = view_cspy(
        crystals if crystals else mol,
        extra_data=extract_crystal_metadata if crystals else None,
        clip_distance=clip_distance_slider.value,
        style=style_dropdown.value,
        background_color="#0f172a",
        show_axes=True,
        compute_extra_data=True,
        multi_traj=False,
        trajectory_slider=True if crystals else False,
        fog=True,
        fog_strength=0.5,
        draw_outlines=True,
        measuring_tool=True,
        recording_tools=True,
        record_include_bgd=True,
        record_include_ui=True,
        viewer_outline="1px solid #334155",
        height="450px",
        unwrap_molecules=False
    )

    status_msg = f"Generated **{len(crystals)}** crystal candidate(s) across space groups: **{valid_space_groups}** with $Z'={z_prime}$."
    if invalid_tokens:
        status_msg += f" *(Ignored out-of-range space groups: {invalid_tokens})*"
    mo.vstack([mo.md(status_msg), viewer])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    > 💡 **Tip**: Click the **List icon (📋)** on the top-right toolbar inside the viewer to open the **Extra Data drawer**.
    > Notice that the **`space group`** and **`Z'`** metadata supplied by your custom `extra_data` callable appear alongside
    > the automatically computed crystallographic properties (density, volume, unit cell dimensions).
    """)
    return


if __name__ == "__main__":
    app.run()
