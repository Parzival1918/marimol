# marimol

> **Fast, reactive, and beautiful 3D molecular and crystal visualizer for [marimo](https://marimo.io) notebooks.**

[![PyPI version](https://img.shields.io/pypi/v/marimol.svg)](https://pypi.org/project/marimol/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![marimol demo](recordings/benzene.gif)

---

**marimol** provides a clean, responsive, and interactive 3D WebGL molecular viewer built with [Three.js](https://threejs.org/) and [anywidget](https://anywidget.dev/). It is designed from the ground up for [marimo](https://marimo.io/) notebooks, enabling **two-way reactivity**: clicking atoms or playing through trajectories in the 3D viewport immediately updates downstream reactive notebook cells in real time.

Supports visualization of **ASE**, **Pymatgen**, **mol-cspy**, and native Python dictionaries with zero configuration.

For a more in depth documentation which includes interactive examples see: [marimol.naujordep.com](https://marimol.naujordep.com).

---

## ✨ Features

- ⚛️ **Multi-format Support**: Native visualizer functions for **ASE** (`ase.Atoms`), **Pymatgen** (`pymatgen.core.Structure` / `Molecule`), **mol-cspy** (`cspy.Crystal` / `cspy.Molecule`), and standard Python dictionaries.
- ⚡ **Two-Way marimo Reactivity**: Downstream cells automatically re-run when you click atoms (`viewer.selected_atoms`) or scrub frames (`viewer.current_frame`).
- 🎬 **Trajectory Playback**: Smooth multi-frame animations with play/pause, step forward/backward, configurable FPS, and an interactive frame scrubber slider.
- 📐 **Measurement Tool**: Built-in interactive ruler for measuring interatomic distances ($\text{Å}$), bond angles ($^\circ$), and dihedral / torsion angles ($^\circ$).
- 🧭 **Coordinate Axis Snapping**: Interactive XYZ triad in the corner—click **X**, **Y**, or **Z** to instantly align the camera along Cartesian axes.
- 🧊 **Crystallography & Periodic Boundaries**: Unit cell bounding boxes, crystallographic lattice vector indicators ($a, b, c$), and automatic molecule unwrapping across periodic boundary conditions (`unwrap_molecules=True`).
- 🎨 **Visual Styles & Cel Shading**: Ball-and-stick, Van der Waals (VDW), wireframe, stylized cartoon silhouette outlines (`draw_outlines=True`), atom element/index labels (`draw_labels=True`), depth fog, and custom styles.
- 📊 **Metadata Drawer**: Instant inspection of unit cell parameters ($a, b, c, \alpha, \beta, \gamma$), volume, density, and custom calculation results.
- 📸 **Image Capture & Video Recording** *(added in v0.2.0)*: High-resolution PNG screenshots (<kbd>S</kbd>) and WebM/MP4 animation recordings (<kbd>R</kbd>) of trajectories or auto-spin loops directly to your downloads.
- ❓ **Interactive Help & Controls Overlay** *(added in v0.2.0)*: Built-in cheatsheet of all keyboard and mouse interactions (toggle with <kbd>H</kbd> or the <kbd>?</kbd> button).

---

## 📦 Installation

Install **marimol** via `pip`:

```bash
pip install marimol
```

To install with support for scientific packages (**ASE**, **Pymatgen**, and **mol-cspy**):

```bash
# Install all optional dependencies
pip install "marimol[external]"

# Or install individual libraries as needed
pip install "marimol[ase]"
pip install "marimol[pymatgen]"
pip install "marimol[cspy]"
```

---

## 🚀 Quick Start

### 1. Visualizing with ASE

```python
import marimo as mo
from ase.build import molecule
from marimol import view_ase

# Visualize a molecule
mol = molecule("CH4")
view_ase(mol)
```

### 2. Visualizing with Pymatgen

```python
from pymatgen.core import Lattice, Structure
from marimol import view_pymatgen

# Visualize a periodic crystal structure
lattice = Lattice.cubic(4.2)
structure = Structure(lattice, ["Cs", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])

view_pymatgen(structure, show_axes=True, draw_outlines=True)
```

### 3. Visualizing with mol-cspy

```python
from cspy import Molecule
from marimol import view_cspy

mol = Molecule.load("aspirin.xyz")
view_cspy(mol, style="ball-and-stick")
```

### 4. Native Python Dictionary / Trajectory

```python
from marimol import view_structure

# Single structure or list of frames for trajectories
data = {
    "positions": [[0.0, 0.0, 0.0], [1.1, 0.0, 0.0]],
    "species": ["C", "O"],
    "bonds": [{"source": 0, "target": 1}],
    # Optional 3D vector arrows (origin, end/direction, length, styling) *(added in v0.3.0)*
    "vectors": [
        {"origin": 0, "direction": [0.0, 0.0, 1.0], "length": 1.5, "color": "yellow", "outline": True},
    ],
}

view_structure(data)
```

---

## 🔄 Two-Way Reactivity in marimo

Because `marimol` widgets connect directly to marimo's reactive dataflow graph, you can access and respond to user interactions in downstream notebook cells:

```python
# Cell 1: Render the viewer and assign to a variable
viewer = view_ase(mol)
viewer
```

```python
# Cell 2: Automatically updates whenever the user selects atoms in the 3D viewer!
selected_indices = viewer.selected_atoms
f"Selected {len(selected_indices)} atom(s): {selected_indices}"
```

```python
# Cell 3: Access current frame during trajectory playback
current_step = viewer.current_frame
f"Currently viewing trajectory frame: {current_step}"
```

---

## 🎛️ Interactive Controls Panel *(added in v0.4.0)*

When visual parameters are passed directly into a viewer cell, changing them re-runs the cell and resets the camera viewpoint. **marimol** provides **`viewer.controls()`** to create a pre-wired marimo UI control panel that mutates settings (background color, style, spin, projection, outlines, transparency, etc.) in real time without re-running the viewer cell or resetting the camera:

```python
# Cell 1: Instantiate the viewer once
viewer = view_ase(mol)
viewer
```

```python
# Cell 2: Display interactive controls (updates 3D scene smoothly in place)
controls = viewer.controls(layout="grid")
controls
```

### Layout Options
- `layout="grid"` (default): Clean multi-column grouped layout (Appearance, Motion, Display & Tools).
- `layout="accordion"`: Compact collapsible sections (`mo.accordion`).
- `layout="tabs"`: Tabbed navigation (`mo.ui.tabs`).
- `layout="vertical"` / `layout="horizontal"`: Single row or column stack.

### Custom Layouts with Individual Controls
You can also unpack or embed individual pre-wired controls anywhere in your custom notebook layouts:

```python
mo.hstack([controls.background, controls.style, controls.spin, controls.spin_speed])
```

### 📄 Exporting & Reusing Configurations
You can extract the live configuration from the controls panel (or directly from the viewer) as a **TOML string**, **dictionary**, or **file**, and reuse it across other viewers with the `config` parameter:

```python
# Cell 3: Live reactive configuration export (automatically updates when controls change!)
toml_config = controls.to_toml()  # or controls.to_dict() / viewer.to_toml()
```

```python
# Cell 4: Save configuration to disk
controls.save_toml("my_theme.toml")  # or viewer.save_config("my_theme.toml")

# Cell 5: Apply the saved theme to other viewers
other_viewer = view_ase(other_mol, config="my_theme.toml")
# or pass the live TOML string / dict directly:
other_viewer = view_ase(other_mol, config=controls.to_dict())
```

---

## 🎮 Viewer Controls & Shortcuts

| Action | Control |
| :--- | :--- |
| **Rotate** | Left-click + Drag |
| **Pan** | Right-click + Drag |
| **Zoom** | Scroll wheel / Pinch trackpad |
| **Select / Inspect Atom** | Click atom (displays index, species, coords in info panel) |
| **Multi-select Atoms** | <kbd>Shift</kbd> + Click atoms |
| **Clear Selection** | Click on background canvas |
| **Snap View to Axis** | Click **X**, **Y**, or **Z** on the bottom-left coordinate triad |
| **Measurement Tool** | Click the **Ruler icon** (top-right), then pick 2 (dist), 3 (angle), or 4 (dihedral) atoms |
| **Extra Data Drawer** | Click the **List icon** (top-right) to expand the metadata drawer |
| **Capture Screenshot** | Click the **Camera icon** or press <kbd>S</kbd> (when `recording_tools=True`) *(added in v0.2.0)* |
| **Record Animation** | Click the **Video icon** or press <kbd>R</kbd> (when `recording_tools=True`) *(added in v0.2.0)* |
| **Help & Shortcuts** | Press <kbd>H</kbd> or click the <kbd>?</kbd> icon to open the controls overlay *(added in v0.2.0)* |
| **Close Help** | Press <kbd>Esc</kbd> or click outside the modal *(added in v0.2.0)* |

---

## ⚙️ Configuration & Parameters

All viewer functions (`view_structure`, `view_ase`, `view_pymatgen`, `view_cspy`) accept the following arguments:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `data` / `atoms` / `structure` | `dict` \| `list[dict]` | *Required* | Structure dictionary, list of dictionaries, or external library structure object. |
| `config` | `dict` \| `str` \| `PathLike` | `None` | Configuration dictionary, TOML string, or path to a `.toml` file. Explicit arguments will overwrite config settings. *(added in v0.2.0)* |
| `style` | `str` \| `dict` | `"ball-and-stick"` | Representation style: `"ball-and-stick"`, `"vdw"`, `"wireframe"`, or custom `dict`. |
| `background_color` | `str` | `"white"` | Viewport background color (e.g. `"white"`, `"black"`, `"#1e1e1e"`, `"transparent"`). |
| `show_axes` | `bool` | `False` | Display interactive XYZ coordinate triad in the bottom-left corner. |
| `projection` | `str` | `"orthographic"` | Camera projection: `"orthographic"` (parallel projection) or `"perspective"`. |
| `width` | `str` | `"100%"` | CSS width of the viewer container (e.g. `"100%"`, `"600px"`). |
| `height` | `str` | `"400px"` | CSS height of the viewer container (e.g. `"400px"`, `"500px"`). |
| `viewer_outline` | `bool` \| `str` | `False` | Draw border around the viewport. `True` for subtle border or CSS border string. |
| `fog` | `bool` | `False` | Distance fog effect for depth cueing in large lattices. |
| `fog_strength` | `float` | `0.5` | Strength of the fog effect ($0.0$ to $1.0$). |
| `clip_distance` | `float` | `0.0` | Near camera clipping plane distance in Å. If `0.0` (default), near clipping is disabled. If positive, clips atoms closer to the camera than this distance. *(added in v0.3.0)* |
| `draw_outlines` | `bool` | `False` | Stylized cartoon / cel-shaded silhouette outlines around atoms and bonds. |
| `draw_labels` | `bool` | `False` | Element and index labels on atoms with 3D occlusion testing. |
| `measuring_tool` | `bool` | `False` | Enable ruler button in the top-right toolbar for distance and angle measurements. |
| `unwrap_molecules` | `bool` | `False` | Unwrap molecules split across periodic unit cell boundary conditions. |
| `structure_transparency` | `float` | `0.0` | Transparency level for atoms and bonds ($0.0$ opaque to $1.0$ fully transparent), useful for viewing internal vectors. *(added in v0.3.0)* |
| `vector_width` | `float` | `0.08` | Shaft radius / width for 3D vector arrows. *(added in v0.3.0)* |
| `vector_outline` | `bool` \| `str` | `False` | Whether to draw outlines around 3D vector arrows (or outline color string). *(added in v0.3.0)* |
| `vector_color` | `str` | `"red"` | Default color name or hex code for 3D vector arrows. *(added in v0.3.0)* |
| `spin` | `bool` | `False` | Continuous automatic 3D rotation of the structure. |
| `spin_axis` | `tuple[float, float, float]` | `(0.0, 1.0, 0.0)` | Cartesian 3D axis vector around which the structure rotates during spin. |
| `spin_speed` | `float` | `2.0` | Angular rotation speed for auto-spin (positive for CW, negative for CCW). |
| `multi_traj` | `bool` | `True` | Trajectory media playback controls (play/pause) for multi-frame data. |
| `traj_fps` | `float` | `10.0` | Playback speed in frames per second for trajectory animations. |
| `trajectory_slider` | `bool` | `False` | Scrubbable timeline slider in the trajectory control bar. |
| `compute_extra_data` | `bool` | `False` | Automatically compute density, volume, lattice lengths & angles, atom count, and MW for the metadata drawer. |
| `extra_data` | `Callable[[T], dict]` | `None` | Custom callable accepting the structure/object and returning a dictionary of metadata for the extra data drawer (only available in `view_ase`, `view_pymatgen`, `view_cspy`). *(added in v0.3.0)* |
| `show_help` | `bool` | `True` | Show the help button and enable the <kbd>H</kbd> interactive controls overlay. *(added in v0.2.0)* |
| `recording_tools` | `bool` | `False` | Show screenshot (PNG) and video recording (WebM/MP4) buttons in the viewer toolbar. *(added in v0.2.0)* |
| `dpi` | `int` | `200` | Resolution in dots per inch (DPI) for exported screenshots and video recordings. *(added in v0.2.0)* |
| `record_include_bgd` | `bool` | `False` | Include the background color in exported screenshots and video recordings (default is `False` for transparent backgrounds). *(added in v0.2.0)* |
| `record_include_ui` | `bool` | `False` | Include all viewer UI elements (playback controls, info panel, measurements, labels) in exported screenshots and video recordings. *(added in v0.2.0)* |

---

### Configuration Presets (TOML / Dict) *(added in v0.2.0)*

You can maintain reusable visual presets across your notebooks using TOML strings, `.toml` files, or dictionaries:

```python
toml_config = """
style = "ball-and-stick"
background_color = "#0f172a"
show_axes = true
spin = true
spin_speed = 1.5
measuring_tool = true
recording_tools = true
record_include_bgd = true
"""

# Explicit arguments take precedence and overwrite config values
view_structure(data, config=toml_config, background_color="#1e293b")
```

---

### Custom Style Configuration

Pass a custom dictionary to `style`:

```python
custom_style = {
    "bond_radius": 0.12,  # Cylinder radius for bonds in Å (0.0 hides bonds)
    "atomic_radius_scaler": 0.8,  # Scale factor multiplied by atomic/VdW radii
    "hydrogen_atom_radius": 0.2,  # Fixed radius override for hydrogen atoms
    "fixed_atomic_radius": None,  # Fixed radius override for all non-H atoms
    "use_vdw_radii": False,  # True for Van der Waals radii; False for covalent
}

view_structure(data, style=custom_style)
```

---

## 🚀 Interactive Examples

Interactive marimo example notebooks demonstrating molecules, trajectories, crystals, and presets are provided in the [`examples/`](examples/) directory:

```bash
# Launch interactive marimo editor for all examples
uv run just examples

# Or edit a specific example notebook
uv run marimo edit examples/01_interactive_molecule_viewer.py
```

| Notebook | Description |
| :--- | :--- |
| [`01_interactive_molecule_viewer.py`](examples/01_interactive_molecule_viewer.py) | Molecule visualization with UI controls (styles, themes, outlines, auto-spin) and two-way reactivity. |
| [`02_trajectory_and_animation.py`](examples/02_trajectory_and_animation.py) | Multi-frame vibrational trajectory with media controls, scrubbable timeline, and video recording. |
| [`03_crystal_structures_and_extra_data.py`](examples/03_crystal_structures_and_extra_data.py) | Periodic crystal lattices with unit cell wireframes, depth fog, and automated crystallographic metrics. |
| [`04_toml_presets_and_themes.py`](examples/04_toml_presets_and_themes.py) | Reusable visual presets loaded from TOML via `config` with parameter overrides. *(added in v0.2.0)* |
| [`05_cspy_crystal_generation_and_custom_extra_data.py`](examples/05_cspy_crystal_generation_and_custom_extra_data.py) | Crystal structure generation across space groups with custom `extra_data` callable. *(added in v0.3.0)* |
| [`06_vector_data_and_arrows.py`](examples/06_vector_data_and_arrows.py) | 3D vector arrows for molecular dipole moments, vibrational forces, magnetic spins, and transparency. *(added in v0.3.0)* |
| [`07_interactive_controls_panel.py`](examples/07_interactive_controls_panel.py) | Pre-wired control panel with live TOML export and theme persistence across viewers, allowing to change the viewer settings without rerunning the cell. *(added in v0.4.0)* |

---

## 📝 Documentation

To run the interactive marimo documentation app locally:

```bash
uv run just docs-edit
```

---

## Contributing

Contributions to **marimol** are very welcome! Whether you are reporting issues, adding support for new computational chemistry packages, improving WebGL performance, or enhancing documentation, here is how to get started:

> [!IMPORTANT]
> **Branching Model**: Active development takes place on the **`dev`** branch. All new feature branches and pull requests should be based on and opened against **`dev`**. The **`main`** branch is reserved for stable releases; changes in `dev` will be merged into `main` when a new release candidate is ready.

### 1. Fork and clone the repository

1. Fork the [marimol repository](https://github.com/Parzival1918/marimol) to your own GitHub account by clicking the **Fork** button on GitHub.
2. Clone your personal fork locally and switch to the `dev` branch:

```bash
git clone https://github.com/<your-username>/marimol.git
cd marimol
git checkout dev
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

### 5. Previewing documentation & examples

To launch and edit the interactive documentation notebook locally:

```bash
uv run just docs-edit
```

To launch and browse the interactive example notebooks:

```bash
uv run just examples
```

To test exporting the documentation to HTML:

```bash
uv run just docs-build
```

### 6. Submitting a Pull Request

1. Make sure your local `dev` branch is up to date:
   ```bash
   git checkout dev
   git pull origin dev
   ```
2. Create a feature branch branching off `dev`:
   ```bash
   git checkout -b feature/my-new-feature
   ```
3. Make your changes and commit them:
   ```bash
   git commit -m "feat: add support for XYZ"
   ```
4. Run checks to verify code formatting and tests:
   ```bash
   uv run just check
   ```
5. Push to your fork:
   ```bash
   git push origin feature/my-new-feature
   ```
6. Open a Pull Request from your feature branch to the **`dev`** branch of [Parzival1918/marimol](https://github.com/Parzival1918/marimol).

---

## 📄 License

Distributed under the [MIT License](LICENSE).
