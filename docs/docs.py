import marimo

__generated_with = "0.23.16"
app = marimo.App()

with app.setup:
    import marimo as mo
    import numpy as np
    from ase.build import bulk, molecule
    from cspy import Molecule
    from cspy.crystal.generate_crystal import CrystalGenerator
    from marimol import view_ase, view_cspy, view_pymatgen, view_structure
    from pymatgen.core import Lattice, Structure


@app.cell(hide_code=True)
def _():
    mo.md(rf"""
    {mo.outline(label="Outline")}

    # marimol

    > A Python package to visualize molecules, crystals, and periodic structures in marimo notebooks.

    **marimol** provides a clean, reactive, and interactive 3D WebGL molecular viewer built with [Three.js](https://threejs.org/) and [anywidget](https://anywidget.dev/). It supports **ase.Atoms**, **pymatgen.core.Structure**, **cspy.Crystal** / **cspy.Molecule**, and custom Python dictionaries out of the box.

    It enables two-way reactivity with marimo, allowing you to select atoms or scrub through trajectories and immediately react to those interactions in downstream notebook cells.

    ---

    ## Installation

    Install **marimol** via `pip`:

    ```bash
    pip install marimol
    ```

    To install optional dependencies for external scientific libraries (**ASE**, **Pymatgen**, and **mol-cspy**):

    ```bash
    pip install "marimol[external]"
    ```

    ---

    ## Quick start

    To visualize a molecular or crystal structure, import the viewer function corresponding to your data format:

    ```python
    # For marimol's native dictionary data format
    from marimol import view_structure

    # For ASE Atoms objects
    from marimol import view_ase

    # For Pymatgen Structure objects
    from marimol import view_pymatgen

    # For CSPY Molecule or Crystal objects
    from marimol import view_cspy
    ```

    Pass a single structure object (or a list of structures for a trajectory). For example, visualizing a methane molecule with **ASE**:

    ```python
    from ase.build import molecule
    from marimol import view_ase

    mol = molecule("CH4")
    view_ase(mol)
    ```

    Which renders the interactive viewer below:
    """)
    return


@app.cell
def _():
    def methane_viz():
        _mol = molecule("CH4")
        return view_ase(_mol)

    methane_viz()
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Viewer controls

    The **marimol** viewer includes rich interactive 3D navigation, atom picking, and measurement capabilities:

    - **Rotate**: Left-click and drag anywhere on the canvas to rotate the 3D structure.
    - **Zoom**: Scroll with the mouse wheel (or pinch on trackpads) to zoom in and out.
    - **Pan / Move**: Right-click and drag to translate the camera view across the screen without moving the center of rotation.
    - **Snap to Axis**: Click on the **X**, **Y**, or **Z** label on the bottom-left coordinate triad to instantly align the camera along that principal Cartesian axis.
    - **Atom Selection & Inspection**:
      - **Single Selection**: Left-click any atom to select it. The atom is highlighted with a cyan ring, and an info card appears at the bottom right displaying its index, element symbol, and Cartesian coordinates $[x, y, z]$.
      - **Multi-Selection**: Hold <kbd>Shift</kbd> while clicking atoms to select or deselect multiple atoms.
      - **Deselect**: Click anywhere on the empty background (without <kbd>Shift</kbd>) to clear the selection.
    - **Reactive Python State**:
      - The returned widget connects directly to marimo's reactive graph!
      - `viewer.selected_atoms`: A Python list of integers containing the 0-based indices of all currently selected atoms (e.g. `[0, 2]`). Whenever you click atoms in the viewer, any downstream marimo cells referencing `viewer.selected_atoms` automatically re-execute.
      - `viewer.current_frame`: An integer indicating the currently active frame index (0-indexed) during trajectory playback.
    - **Measurement Tool**:
      - Click the **Ruler icon** in the top-right overlay to toggle measurement mode:
        - Click **2 atoms** to measure the interatomic distance ($\text{Å}$).
        - Click **3 atoms** to measure the bond angle ($^\circ$).
        - Click **4 atoms** to measure the dihedral / torsion angle ($^\circ$).
      - Click the ruler button again or click empty canvas space to exit measurement mode.
    - **Extra Data Drawer**:
      - Click the **List icon** in the top-right overlay to expand the metadata drawer, showing properties such as unit cell volume, density, lattice parameters ($a, b, c, \alpha, \beta, \gamma$), atom counts, or custom calculation results.
    - **Trajectory Controls**:
      - When visualizing a list of frames, a media player overlay appears with buttons for First, Previous, Play/Pause, Next, and Last frame, as well as an optional scrubbable frame slider.

    ---

    ## Viewer arguments

    All viewer functions (`view_structure`, `view_ase`, `view_pymatgen`, `view_cspy`) accept the following configuration parameters:

    | Parameter | Type | Default | Description |
    | :--- | :--- | :--- | :--- |
    | `data` / `atoms` / `structure` | `dict` \| `list[dict]` | *Required* | Structure dictionary or list of dictionaries (or `ase.Atoms`, `pymatgen.core.Structure`, `cspy.Crystal` / `cspy.Molecule`). |
    | `style` | `str` \| `dict` | `"ball-and-stick"` | Visual representation style: `"ball-and-stick"`, `"vdw"`, `"wireframe"`, or a custom style dictionary. |
    | `background_color` | `str` | `"white"` | Viewport background color (e.g. `"white"`, `"black"`, `"transparent"`, `"#1e1e1e"`). |
    | `show_axes` | `bool` | `False` | Whether to display the interactive XYZ coordinate triad in the bottom-left corner. |
    | `projection` | `str` | `"orthographic"` | Camera projection type: `"orthographic"` (parallel projection, ideal for crystallography and measurements) or `"perspective"`. |
    | `width` | `str` | `"100%"` | CSS width of the viewer container (e.g. `"100%"`, `"600px"`). |
    | `height` | `str` | `"400px"` | CSS height of the viewer container (e.g. `"400px"`, `"500px"`). |
    | `viewer_outline` | `bool` \| `str` | `False` | Draws a border around the viewer container. Set `True` for a subtle grey outline or pass a CSS border string (e.g. `"1px solid #ccc"`). |
    | `fog` | `bool` | `False` | Enables distance fog effect for depth cueing in large lattices. |
    | `fog_strength` | `float` | `0.5` | Strength of the fog effect (0.0 to 1.0). |
    | `draw_outlines` | `bool` | `False` | Draws stylized cartoon / cel-shaded silhouette outlines around atoms and bonds. |
    | `draw_labels` | `bool` | `False` | Displays element/index labels on top of atoms with 3D occlusion testing. |
    | `measuring_tool` | `bool` | `False` | Enables the ruler button in the top-right overlay for distance, angle, and dihedral measurements. |
    | `unwrap_molecules` | `bool` | `False` | Unwraps molecules split across periodic unit cell boundary conditions and centers whole molecules inside the cell. |
    | `spin` | `bool` | `False` | Enables continuous automatic 3D rotation of the structure. |
    | `spin_axis` | `tuple[float, float, float]` | `(0.0, 1.0, 0.0)` | Cartesian 3D axis vector around which the structure rotates during auto-spin. |
    | `spin_speed` | `float` | `2.0` | Angular rotation speed for auto-spin (positive for clockwise, negative for counter-clockwise). |
    | `multi_traj` | `bool` | `True` | Displays trajectory media playback controls (play/pause) for multi-frame data. |
    | `traj_fps` | `float` | `10.0` | Playback speed in frames per second for trajectory animations. |
    | `trajectory_slider` | `bool` | `False` | Displays a scrubbable timeline slider in the trajectory control bar. |
    | `compute_extra_data` | `bool` | `False` | Automatically computes physical/crystallographic properties (density, volume, lattice lengths & angles, atom count, molecular weight) for the info drawer. |

    ### Custom Style Dictionaries

    When specifying a custom `dict` for the `style` argument, you can configure:

    ```python
    custom_style = {
        "bond_radius": 0.12,              # Cylinder radius for bonds in Angstroms (0.0 hides bonds)
        "atomic_radius_scaler": 0.8,       # Scale factor multiplied by atomic/VdW radii
        "hydrogen_atom_radius": 0.2,       # Fixed radius override for hydrogen atoms
        "fixed_atomic_radius": None,       # If set, gives all non-H atoms a fixed radius in Angstroms
        "use_vdw_radii": False,            # True uses Van der Waals radii; False uses covalent radii
    }
    ```

    ---

    ## Data structure

    **marimol** operates natively on a clean dictionary format. If you are not using ASE, Pymatgen, or CSPY, you can pass structures directly using standard Python dictionaries:

    ```python
    structure_dict = {
        # [Required] Cartesian coordinates in Angstroms (Nx3 list)
        "positions": [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 1.089],
            [1.026, 0.0, -0.363],
            [-0.513, -0.889, -0.363],
            [-0.513, 0.889, -0.363],
        ],

        # [Required] Chemical element symbols or atomic numbers
        "species": ["C", "H", "H", "H", "H"],

        # [Optional] Explicit covalent bonds (auto-computed if omitted and bond_radius > 0)
        "bonds": [
            {"source": 0, "target": 1},
            {"source": 0, "target": 2},
            {"source": 0, "target": 3},
            {"source": 0, "target": 4},
        ],

        # [Optional] 3x3 lattice vectors in Angstroms for periodic crystal structures
        "unit_cell": [
            [10.0, 0.0, 0.0],
            [0.0, 10.0, 0.0],
            [0.0, 0.0, 10.0],
        ],

        # [Optional] Custom atom text labels when draw_labels=True
        "labels": ["C_center", "H1", "H2", "H3", "H4"],

        # [Optional] List of atom indices to highlight with an outline
        "highlight": [0],

        # [Optional] Arbitrary key-value metadata shown in the extra data drawer
        "extra_data": {
            "energy": -40.512,
            "point_group": "Td",
        },
    }
    ```

    ### Trajectories

    A trajectory is simply a Python `list[dict]` containing multiple structure dictionaries in sequence:

    ```python
    trajectory_data = [frame_0, frame_1, frame_2, ...]
    ```

    ---

    ## Examples

    Below are examples showcasing different data formats, visual styles, and viewer capabilities. Click **View Code** on any example to expand its implementation.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### 1. Custom Data Dictionary: Benzene Ring with Cel-Shaded Outlines & Measurement Tool

    Visualizing a planar benzene ($\text{C}_6\text{H}_6$) molecule defined via a Python dictionary, featuring cartoon/cel-shaded outlines (`draw_outlines=True`), the interactive measurement tool (`measuring_tool=True`), and the XYZ coordinate triad (`show_axes=True`).
    """)
    return


@app.cell
def _():
    _code = mo.accordion({
        "View Code": mo.md(r"""
    ```python
    from marimol import view_structure

    benzene = {
        "positions": [
            [0.0, 1.397, 0.0],
            [1.210, 0.698, 0.0],
            [1.210, -0.698, 0.0],
            [0.0, -1.397, 0.0],
            [-1.210, -0.698, 0.0],
            [-1.210, 0.698, 0.0],
            [0.0, 2.479, 0.0],
            [2.147, 1.239, 0.0],
            [2.147, -1.239, 0.0],
            [0.0, -2.479, 0.0],
            [-2.147, -1.239, 0.0],
            [-2.147, 1.239, 0.0],
        ],
        "species": ["C", "C", "C", "C", "C", "C", "H", "H", "H", "H", "H", "H"],
    }

    view_structure(
        benzene,
        style="ball-and-stick",
        draw_outlines=True,
        measuring_tool=True,
        show_axes=True,
        viewer_outline=True,
        background_color="#f8fafc",
    )
    ```
    """)
    })

    _benzene = {
        "positions": [
            [0.0, 1.397, 0.0],
            [1.210, 0.698, 0.0],
            [1.210, -0.698, 0.0],
            [0.0, -1.397, 0.0],
            [-1.210, -0.698, 0.0],
            [-1.210, 0.698, 0.0],
            [0.0, 2.479, 0.0],
            [2.147, 1.239, 0.0],
            [2.147, -1.239, 0.0],
            [0.0, -2.479, 0.0],
            [-2.147, -1.239, 0.0],
            [-2.147, 1.239, 0.0],
        ],
        "species": ["C", "C", "C", "C", "C", "C", "H", "H", "H", "H", "H", "H"],
    }
    _viewer = view_structure(
        _benzene,
        style="ball-and-stick",
        draw_outlines=True,
        measuring_tool=True,
        show_axes=True,
        viewer_outline=True,
        background_color="#f8fafc",
    )

    mo.vstack([_code, _viewer])
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### 2. Trajectory Playback: Water Molecular Vibration with Timeline Slider

    Visualizing an animated trajectory of a vibrating water ($\text{H}_2\text{O}$) molecule using `multi_traj=True`, `trajectory_slider=True`, and `traj_fps=15.0`.
    """)
    return


@app.cell
def _():
    _code = mo.accordion({
        "View Code": mo.md(r"""
    ```python
    import numpy as np
    from marimol import view_structure

    # Generate harmonic bending & stretching trajectory frames
    frames = []
    for t in np.linspace(0, 2 * np.pi, 24, endpoint=False):
        d = 0.96 + 0.12 * np.sin(t)
        angle = np.radians(104.5 + 12 * np.cos(t))
        frames.append({
            "positions": [
                [0.0, 0.0, 0.12],
                [0.0, d * np.sin(angle / 2), -d * np.cos(angle / 2)],
                [0.0, -d * np.sin(angle / 2), -d * np.cos(angle / 2)],
            ],
            "species": ["O", "H", "H"],
        })

    view_structure(
        frames,
        multi_traj=True,
        trajectory_slider=True,
        traj_fps=15.0,
        show_axes=True,
        viewer_outline=True,
    )
    ```
    """)
    })

    _frames = []
    for _t in np.linspace(0, 2 * np.pi, 24, endpoint=False):
        _d = 0.96 + 0.12 * np.sin(_t)
        _angle = np.radians(104.5 + 12 * np.cos(_t))
        _frames.append({
            "positions": [
                [0.0, 0.0, 0.12],
                [0.0, _d * np.sin(_angle / 2), -_d * np.cos(_angle / 2)],
                [0.0, -_d * np.sin(_angle / 2), -_d * np.cos(_angle / 2)],
            ],
            "species": ["O", "H", "H"],
        })

    _viewer = view_structure(
        _frames,
        multi_traj=True,
        trajectory_slider=True,
        traj_fps=15.0,
        show_axes=True,
        viewer_outline=True,
    )

    mo.vstack([_code, _viewer])
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### 3. ASE Integration: Silicon Diamond Bulk Crystal with Computed Extra Data

    Visualizing a cubic Silicon unit cell built with **ASE** (`ase.build.bulk`), demonstrating automatic property computation (`compute_extra_data=True`), periodic boundary condition handling (`unwrap_molecules=True`), and interactive coordinate axes (`show_axes=True`). Click the list icon in the upper-right to inspect computed crystallographic metrics (density, volume, lattice constants).
    """)
    return


@app.cell
def _():
    _code = mo.accordion({
        "View Code": mo.md(r"""
    ```python
    from ase.build import bulk
    from marimol import view_ase

    # Create cubic diamond silicon unit cell
    si_crystal = bulk("Si", "diamond", cubic=True)

    view_ase(
        si_crystal,
        compute_extra_data=True,
        show_axes=True,
        unwrap_molecules=True,
        viewer_outline=True,
    )
    ```
    """)
    })

    _si = bulk("Si", "diamond", cubic=True)
    _viewer = view_ase(
        _si,
        compute_extra_data=True,
        show_axes=True,
        unwrap_molecules=True,
        viewer_outline=True,
    )

    mo.vstack([_code, _viewer])
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### 4. Pymatgen Integration: Perovskite $\text{SrTiO}_3$ in Van der Waals Style with Depth Fog

    Visualizing a Strontium Titanate ($\text{SrTiO}_3$) perovskite crystal created with **Pymatgen** (`pymatgen.core.Structure`), rendered in space-filling Van der Waals sphere style (`style="vdw"`), perspective projection (`projection="perspective"`), and atmospheric depth fog (`fog=True`, `fog_strength=0.6`).
    """)
    return


@app.cell
def _():
    _code = mo.accordion({
        "View Code": mo.md(r"""
    ```python
    from pymatgen.core import Lattice, Structure
    from marimol import view_pymatgen

    # Create cubic perovskite SrTiO3 (Spacegroup Pm-3m)
    srtio3 = Structure.from_spacegroup(
        "Pm-3m",
        Lattice.cubic(3.905),
        ["Sr", "Ti", "O"],
        [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5], [0.5, 0.5, 0.0]],
    )

    view_pymatgen(
        srtio3,
        style="vdw",
        projection="perspective",
        fog=True,
        fog_strength=0.6,
        show_axes=True,
        viewer_outline=True,
    )
    ```
    """)
    })

    _srtio3 = Structure.from_spacegroup(
        "Pm-3m",
        Lattice.cubic(3.905),
        ["Sr", "Ti", "O"],
        [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5], [0.5, 0.5, 0.0]],
    )

    _viewer = view_pymatgen(
        _srtio3,
        style="vdw",
        projection="perspective",
        fog=True,
        fog_strength=0.6,
        show_axes=True,
        viewer_outline=True,
    )

    mo.vstack([_code, _viewer])
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### 5. CSPY Integration: Crystal Structure Generation with `CrystalGenerator`

    Visualizing predicted molecular crystal candidates generated with **mol-cspy**'s `CrystalGenerator` (`cspy.crystal.generate_crystal.CrystalGenerator`). Multiple candidate crystal structures are loaded as a collection with interactive trajectory navigation (`multi_traj=False`, `trajectory_slider=True`), and automated crystallographic data computation (`compute_extra_data=True`).
    """)
    return


@app.cell
def _():
    _code = mo.accordion({
        "View Code": mo.md(r"""
    ```python
    from cspy import Molecule
    from cspy.crystal.generate_crystal import CrystalGenerator
    from marimol import view_cspy

    # 1. Define a methane molecule and determine connectivity
    mol = Molecule.from_xyz_string('''5
    methane
    C 2.629 2.629 2.629
    H 2.000 3.258 2.000
    H 3.258 3.258 3.258
    H 2.000 2.000 3.258
    H 3.258 2.000 2.000
    ''')
    mol.guess_bonds()

    # 2. Generate candidate crystal polymorphs in space group P-1 (space group 2)
    generator = CrystalGenerator([mol, mol], space_group=2)
    crystals = []
    for seed in range(1, 30):
        candidate = generator.generate(seed)
        if candidate is not None:
            crystals.append(candidate)
        if len(crystals) == 10:
            break

    # 3. Visualize the generated candidate crystals with frame slider & computed extra data
    view_cspy(
        crystals,
        multi_traj=False,
        trajectory_slider=True,
        compute_extra_data=True,
        unwrap_molecules=True,
        show_axes=True,
        viewer_outline=True,
        fog=True,
    )
    ```
    """)
    })

    _mol = Molecule.from_xyz_string("""5
    methane
    C 2.629 2.629 2.629
    H 2.000 3.258 2.000
    H 3.258 3.258 3.258
    H 2.000 2.000 3.258
    H 3.258 2.000 2.000
    """)
    _mol.guess_bonds()

    _generator = CrystalGenerator([_mol, _mol], space_group=2)
    _crystals = []
    for _seed in range(1, 30):
        _candidate = _generator.generate(_seed)
        if _candidate is not None:
            _crystals.append(_candidate)
        if len(_crystals) == 10:
            break

    _viewer = view_cspy(
        _crystals,
        multi_traj=False,
        trajectory_slider=True,
        compute_extra_data=True,
        show_axes=True,
        viewer_outline=True,
        fog=True,
    )

    mo.vstack([_code, _viewer])
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ---

    ## Contributing

    Contributions to **marimol** are very welcome! Whether you are reporting issues, adding support for new computational chemistry packages, improving WebGL performance, or enhancing documentation, here is how to get started:

    ### 1. Fork and clone the repository

    1. Fork the [marimol repository](https://github.com/Parzival1918/marimol) to your own GitHub account by clicking the **Fork** button on GitHub.
    2. Clone your personal fork locally:

    ```bash
    git clone https://github.com/<your-username>/marimol.git
    cd marimol
    ```

    ### 2. Set up the development environment & pre-commit hooks

    We use [uv](https://github.com/astral-sh/uv) for fast, reproducible dependency management and [just](https://github.com/casey/just) for task automation. Install dependencies with all optional extras and dev tools:

    ```bash
    # Install dependencies with all optional extras and dev tools
    uv sync --all-extras
    ```

    To keep code formatting and linting consistent across the codebase, **pre-commit hooks must be installed**:

    ```bash
    # Install Git hook shims via just or prek
    uv run just install-hooks
    ```

    Once installed, automated checks (such as [Ruff](https://astral.sh/ruff) formatting and linting, trailing whitespace trimming, and YAML validation) will run automatically before every commit.

    ### 3. Code style and formatting

    This project uses [Ruff](https://astral.sh/ruff) for linting and formatting. You can run checks manually at any time:

    ```bash
    # Run linter
    uv run just lint

    # Format code
    uv run just format
    ```

    ### 4. Running tests

    Execute the test suite using `pytest`:

    ```bash
    uv run just test
    ```

    ### 5. Previewing documentation

    To launch and edit the interactive documentation notebook locally:

    ```bash
    uv run just docs-edit
    ```

    To test exporting the documentation to HTML:

    ```bash
    uv run just docs-build
    ```

    ### 6. Submitting a Pull Request

    1. Create a feature branch on your fork: `git checkout -b feature/my-new-feature`
    2. Make your changes and commit them: `git commit -m "feat: add support for XYZ"`
    3. Push to your fork: `git push origin feature/my-new-feature`
    4. Open a Pull Request from your branch to the `main` branch of [Parzival1918/marimol](https://github.com/Parzival1918/marimol).

    ---

    <div align="center" style="margin: 24px 0 12px 0;">
      <a href="https://github.com/Parzival1918/marimol" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: inherit; display: inline-flex; align-items: center; gap: 10px; font-weight: 600; font-size: 16px; padding: 10px 20px; border: 1px solid #e2e8f0; border-radius: 8px; background: #f8fafc; transition: all 0.2s ease;">
        <svg height="24" aria-hidden="true" viewBox="0 0 16 16" version="1.1" width="24" fill="currentColor">
          <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"></path>
        </svg>
        <span>View and Star <strong>marimol</strong> on GitHub (Parzival1918/marimol)</span>
      </a>
    </div>
    """)
    return


if __name__ == "__main__":
    app.run()
