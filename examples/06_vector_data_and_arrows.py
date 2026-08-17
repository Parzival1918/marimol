import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    from ase import units
    from ase.build import molecule
    from ase.calculators.calculator import Calculator, all_changes
    from ase.calculators.emt import EMT
    from ase.cluster import Icosahedron
    from ase.md.velocitydistribution import Stationary, ZeroRotation, thermalize_momenta
    from ase.md.verlet import VelocityVerlet

    from marimol import view_structure

    class FlexibleWaterPotential(Calculator):
        """Flexible water potential with harmonic O-H bonds, Urey-Bradley H-H spring, and LJ+Coulomb."""

        implemented_properties = ["energy", "forces"]

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.k_oh = 25.0  # eV / A^2
            self.r_oh0 = 0.9572  # A
            self.k_hh = 15.0  # eV / A^2 (Urey-Bradley spring, maintains 104.52 deg angle)
            self.r_hh0 = 1.514  # A
            self.eps = 0.0067  # eV
            self.sig = 3.166  # A
            self.q_o = -0.834  # e
            self.q_h = 0.417  # e
            self.k_coul = 14.3996  # eV * A / e^2
            self.r_core = 0.5  # A

        def calculate(self, atoms=None, properties=["energy", "forces"], system_changes=all_changes):
            super().calculate(atoms, properties, system_changes)
            pos = atoms.positions
            n_mol = len(atoms) // 3
            forces = np.zeros_like(pos)
            energy = 0.0

            # 1. Intramolecular terms (O-H1, O-H2, H1-H2)
            for m in range(n_mol):
                o = m * 3
                h1 = o + 1
                h2 = o + 2

                # O-H1 bond
                d_oh1 = pos[h1] - pos[o]
                r_oh1 = np.linalg.norm(d_oh1)
                f_oh1 = -2.0 * self.k_oh * (r_oh1 - self.r_oh0) * (d_oh1 / max(1e-6, r_oh1))
                forces[h1] += f_oh1
                forces[o] -= f_oh1
                energy += self.k_oh * (r_oh1 - self.r_oh0) ** 2

                # O-H2 bond
                d_oh2 = pos[h2] - pos[o]
                r_oh2 = np.linalg.norm(d_oh2)
                f_oh2 = -2.0 * self.k_oh * (r_oh2 - self.r_oh0) * (d_oh2 / max(1e-6, r_oh2))
                forces[h2] += f_oh2
                forces[o] -= f_oh2
                energy += self.k_oh * (r_oh2 - self.r_oh0) ** 2

                # H1-H2 spring
                d_hh = pos[h2] - pos[h1]
                r_hh = np.linalg.norm(d_hh)
                f_hh = -2.0 * self.k_hh * (r_hh - self.r_hh0) * (d_hh / max(1e-6, r_hh))
                forces[h2] += f_hh
                forces[h1] -= f_hh
                energy += self.k_hh * (r_hh - self.r_hh0) ** 2

            # 2. Intermolecular non-bonded terms
            charges = [self.q_o if i % 3 == 0 else self.q_h for i in range(len(atoms))]
            for i in range(len(atoms)):
                for j in range(i + 1, len(atoms)):
                    if i // 3 == j // 3:
                        continue
                    dr = pos[j] - pos[i]
                    r2 = np.dot(dr, dr)
                    r_eff2 = r2 + self.r_core**2
                    r_eff = np.sqrt(r_eff2)
                    q_ij = charges[i] * charges[j]
                    energy += self.k_coul * q_ij / r_eff
                    f_c = (self.k_coul * q_ij / (r_eff2 * r_eff)) * dr
                    forces[j] += f_c
                    forces[i] -= f_c

                    if i % 3 == 0 and j % 3 == 0:
                        r = np.sqrt(r2)
                        sr6 = (self.sig / r) ** 6
                        sr12 = sr6**2
                        energy += 4.0 * self.eps * (sr12 - sr6)
                        f_lj_mag = 24.0 * self.eps * (2.0 * sr12 - sr6) / r2
                        f_lj = f_lj_mag * dr
                        forces[j] += f_lj
                        forces[i] -= f_lj

            self.results["energy"] = energy
            self.results["forces"] = forces

    return (
        EMT,
        FlexibleWaterPotential,
        Icosahedron,
        Stationary,
        VelocityVerlet,
        ZeroRotation,
        mo,
        molecule,
        np,
        thermalize_momenta,
        units,
        view_structure,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # ⚡ Molecular Dynamics with Atomic Force Vectors

    This example demonstrates a live **Molecular Dynamics (MD)** simulation with **ASE**
    and visualizes instantaneous atomic **force vectors** as dynamic 3D arrows with **marimol** *(added in v0.3.0)*.

    At each integration step, the net force vector $\vec{F}_i = -\nabla_i V$ acting on each atom is displayed as a 3D arrow showing the magnitude and direction of the chemical and electrostatic restoring forces.
    """)
    return


@app.cell
def _(mo):
    system_select = mo.ui.dropdown(
        options={
            "💧 Water Trimer (3 H2O Cluster)": "water_3",
            "✨ Gold Nanoparticle (Au13 Cluster - EMT)": "au13",
            "🪙 Platinum Nanocluster (Pt13 Cluster - EMT)": "pt13",
        },
        value="💧 Water Trimer (3 H2O Cluster)",
        label="⚛️ System:",
    )

    temp_slider = mo.ui.slider(
        start=50,
        stop=400,
        step=25,
        value=150,
        label="🌡️ Temperature (K):",
    )

    steps_slider = mo.ui.slider(
        start=20,
        stop=80,
        step=5,
        value=40,
        label="⏱️ Simulation Steps:",
    )

    dt_slider = mo.ui.slider(
        start=0.25,
        stop=1.00,
        step=0.25,
        value=0.50,
        label="⚡ Timestep (fs):",
    )

    force_scale_slider = mo.ui.slider(
        start=0.05,
        stop=1.50,
        step=0.05,
        value=0.30,
        label="📏 Force Arrow Scale:",
    )

    color_mode = mo.ui.dropdown(
        options={
            "🎨 Color by Element": "element",
            "🔥 Force Magnitude Heatmap": "force",
            "⚡ Uniform Cyan Arrows": "uniform",
        },
        value="🎨 Color by Element",
        label="🎯 Vector Colors:",
    )

    vector_width_slider = mo.ui.slider(
        start=0.03,
        stop=0.15,
        step=0.01,
        value=0.07,
        label="📐 Vector Width:",
    )

    transparency_slider = mo.ui.slider(
        start=0.0,
        stop=0.80,
        step=0.05,
        value=0.0,
        label="👻 Structure Transparency:",
    )

    outline_toggle = mo.ui.checkbox(value=True, label="✏️ Vector Outlines")
    spin_toggle = mo.ui.checkbox(value=False, label="🔄 Auto-spin")

    controls = mo.vstack(
        [
            mo.hstack([system_select, color_mode], justify="start"),
            mo.hstack([temp_slider, steps_slider, dt_slider], justify="start"),
            mo.hstack(
                [
                    force_scale_slider,
                    vector_width_slider,
                    transparency_slider,
                ],
                justify="start",
            ),
            mo.hstack([outline_toggle, spin_toggle], justify="start"),
        ]
    )

    mo.accordion({"⚙️ Simulation & Visualization Controls": controls})
    return (
        color_mode,
        controls,
        dt_slider,
        force_scale_slider,
        outline_toggle,
        spin_toggle,
        steps_slider,
        system_select,
        temp_slider,
        transparency_slider,
        vector_width_slider,
    )


@app.cell
def _(
    EMT,
    FlexibleWaterPotential,
    Icosahedron,
    Stationary,
    VelocityVerlet,
    ZeroRotation,
    color_mode,
    dt_slider,
    force_scale_slider,
    molecule,
    np,
    steps_slider,
    system_select,
    temp_slider,
    thermalize_momenta,
    units,
):
    def _build_system(system_key: str):
        """Construct atomic structure with clean initial coordinates."""
        if system_key == "water_3":
            w1 = molecule("H2O")
            w2 = molecule("H2O")
            w2.translate([2.8, 0.0, 0.0])
            w2.rotate(105, "y")
            w3 = molecule("H2O")
            w3.translate([1.4, 2.4, 0.0])
            w3.rotate(-105, "x")
            cluster = w1 + w2 + w3
            cluster.set_cell([25.0, 25.0, 25.0])
            cluster.center()
            cluster.calc = FlexibleWaterPotential()
            return cluster

        symbol = "Au" if system_key == "au13" else "Pt"
        atoms = Icosahedron(symbol, noshells=2)
        atoms.set_cell([20.0, 20.0, 20.0])
        atoms.center()
        atoms.calc = EMT()
        return atoms

    def _get_vector_color(species_sym: str, force_mag: float, max_force: float, mode: str) -> str:
        """Determine vector arrow color based on selected color mode."""
        if mode == "uniform":
            return "#38bdf8"
        if mode == "element":
            palette = {"O": "#38bdf8", "H": "#facc15", "Au": "#fbbf24", "Pt": "#a78bfa"}
            return palette.get(species_sym, "#ef4444")
        # Heatmap (blue -> yellow -> red)
        ratio = min(1.0, max(0.0, force_mag / (max_force if max_force > 0 else 1.0)))
        r = int(255 * ratio)
        g = int(220 * (1.0 - abs(ratio - 0.5) * 2.0))
        b = int(255 * (1.0 - ratio))
        return f"#{r:02x}{g:02x}{b:02x}"

    atoms_sys = _build_system(system_select.value)

    thermalize_momenta(atoms_sys, temperature_K=float(temp_slider.value))
    Stationary(atoms_sys)
    ZeroRotation(atoms_sys)

    dt_fs = float(dt_slider.value)
    dyn_sim = VelocityVerlet(atoms_sys, timestep=dt_fs * units.fs)

    n_steps = int(steps_slider.value)
    f_scale = float(force_scale_slider.value)
    c_mode = color_mode.value

    trajectory_frames = []

    for step_i in range(n_steps):
        dyn_sim.run(1)
        positions = atoms_sys.get_positions().tolist()
        forces = atoms_sys.get_forces()
        species = atoms_sys.get_chemical_symbols()

        f_mags = [float(np.linalg.norm(f)) for f in forces]
        max_f = max(f_mags) if f_mags and max(f_mags) > 0 else 1.0

        frame_vectors = []
        for atom_idx in range(len(atoms_sys)):
            f_atom = forces[atom_idx]
            f_mag = f_mags[atom_idx]
            if f_mag > 1e-7:
                col = _get_vector_color(species[atom_idx], f_mag, max_f, c_mode)
                frame_vectors.append(
                    {
                        "origin": atom_idx,
                        "direction": [float(x) for x in f_atom],
                        "length": float(f_mag * f_scale),
                        "color": col,
                    }
                )

        frame_dict = {
            "positions": positions,
            "species": species,
            "vectors": frame_vectors,
            "extra_data": {
                "Step": step_i + 1,
                "Simulation Time": f"{(step_i + 1) * dt_fs:.1f} fs",
                "Instantaneous Temperature": f"{atoms_sys.get_temperature():.1f} K",
                "Kinetic Energy": f"{atoms_sys.get_kinetic_energy():.3f} eV",
                "Potential Energy": f"{atoms_sys.get_potential_energy():.3f} eV",
                "Max Force": f"{max_f:.3f} eV/Å",
            },
        }
        trajectory_frames.append(frame_dict)

    return (trajectory_frames,)


@app.cell
def _(
    outline_toggle,
    spin_toggle,
    trajectory_frames,
    transparency_slider,
    vector_width_slider,
    view_structure,
):
    viewer = view_structure(
        trajectory_frames,
        vector_width=vector_width_slider.value,
        vector_outline=outline_toggle.value,
        structure_transparency=transparency_slider.value,
        multi_traj=True,
        trajectory_slider=True,
        traj_fps=14.0,
        background_color="#0f172a",
        show_axes=True,
        viewer_outline="1px solid #334155",
        spin=spin_toggle.value,
        spin_speed=1.0,
        measuring_tool=True,
        recording_tools=True,
        record_include_bgd=True,
        record_include_ui=True,
    )

    viewer
    return (viewer,)


@app.cell
def _(mo, trajectory_frames, viewer):
    cur_step = viewer.current_frame
    total_steps = len(trajectory_frames)
    frame_data = trajectory_frames[cur_step] if 0 <= cur_step < total_steps else trajectory_frames[0]
    num_vectors = len(frame_data.get("vectors", []))
    selected = viewer.selected_atoms

    stats_md = f"""
    ### 📊 Live Trajectory Telemetry
    - **Current Frame:** `{cur_step + 1} / {total_steps}`
    - **Active Force Vectors:** `{num_vectors}` atomic force vector(s)
    - **Selected Atom(s):** `{selected if selected else 'None (Click an atom to inspect)'}`
    - **Time:** `{frame_data['extra_data']['Simulation Time']}`
    - **Temperature:** `{frame_data['extra_data']['Instantaneous Temperature']}`
    - **Kinetic Energy:** `{frame_data['extra_data']['Kinetic Energy']}`
    - **Potential Energy:** `{frame_data['extra_data']['Potential Energy']}`
    - **Max Force:** `{frame_data['extra_data'].get('Max Force', 'N/A')}`
    """

    mo.md(stats_md)
    return


if __name__ == "__main__":
    app.run()
