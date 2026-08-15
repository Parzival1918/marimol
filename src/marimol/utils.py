from __future__ import annotations

import copy
import os
import tomllib

import numpy as np

# CPK Colors and standard atomic radii (in Angstroms) for visualization
CPK_COLORS = {
    "H": [1.0, 1.0, 1.0],  # White
    "C": [0.56, 0.56, 0.56],  # Light Grey
    "N": [0.19, 0.31, 0.97],  # Blue
    "O": [1.0, 0.05, 0.05],  # Red
    "F": [0.56, 0.88, 0.31],  # Green
    "Cl": [0.12, 0.94, 0.12],  # Green
    "Br": [0.65, 0.16, 0.16],  # Dark Red
    "I": [0.58, 0.0, 0.58],  # Purple
    "S": [1.0, 0.78, 0.20],  # Yellow
    "P": [1.0, 0.50, 0.0],  # Orange
    "B": [1.0, 0.71, 0.71],  # Peach
    "Si": [0.94, 0.78, 0.63],  # Tan
    "Fe": [0.88, 0.40, 0.20],  # Orange-red
    "Cu": [0.78, 0.50, 0.20],  # Copper
    "Ag": [0.75, 0.75, 0.75],  # Silver
    "Au": [1.0, 0.82, 0.14],  # Gold
}

# Default color for unknown elements (Pink)
DEFAULT_COLOR = [1.0, 0.08, 0.58]

# Common HTML/CSS color names to Hex mapping for backgrounds
NAMED_COLORS = {
    "white": "#ffffff",
    "black": "#000000",
    "red": "#ff0000",
    "green": "#00ff00",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "cyan": "#00ffff",
    "magenta": "#ff00ff",
    "gray": "#808080",
    "grey": "#808080",
    "lightgray": "#d3d3d3",
    "darkgray": "#a9a9a9",
    "transparent": "transparent",
}

# Covalent radii (Angstroms) approx
ATOMIC_RADII = {
    "H": 0.31,
    "C": 0.76,
    "N": 0.71,
    "O": 0.66,
    "F": 0.57,
    "Cl": 1.02,
    "Br": 1.20,
    "I": 1.39,
    "S": 1.05,
    "P": 1.07,
    "B": 0.84,
    "Si": 1.11,
    "Fe": 1.32,
    "Cu": 1.32,
    "Ag": 1.45,
    "Au": 1.36,
}

# Van der Waals radii (Angstroms) approx
VDW_RADII = {
    "H": 1.20,
    "C": 1.70,
    "N": 1.55,
    "O": 1.52,
    "F": 1.47,
    "Cl": 1.75,
    "Br": 1.85,
    "I": 1.98,
    "S": 1.80,
    "P": 1.80,
    "B": 1.92,
    "Si": 2.10,
    "Fe": 2.00,
    "Cu": 1.40,
    "Ag": 1.72,
    "Au": 1.66,
}

# Standard atomic weights (in g/mol) for elements 1 to 118
ATOMIC_WEIGHTS = {
    "H": 1.008,
    "He": 4.0026,
    "Li": 6.94,
    "Be": 9.0122,
    "B": 10.81,
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "F": 18.9984,
    "Ne": 20.180,
    "Na": 22.9898,
    "Mg": 24.305,
    "Al": 26.9815,
    "Si": 28.085,
    "P": 30.9738,
    "S": 32.06,
    "Cl": 35.45,
    "Ar": 39.948,
    "K": 39.0983,
    "Ca": 40.078,
    "Sc": 44.9559,
    "Ti": 47.867,
    "V": 50.9415,
    "Cr": 51.9961,
    "Mn": 54.938,
    "Fe": 55.845,
    "Co": 58.9332,
    "Ni": 58.6934,
    "Cu": 63.546,
    "Zn": 65.38,
    "Ga": 69.723,
    "Ge": 72.630,
    "As": 74.9216,
    "Se": 78.971,
    "Br": 79.904,
    "Kr": 83.798,
    "Rb": 85.4678,
    "Sr": 87.62,
    "Y": 88.9058,
    "Zr": 91.224,
    "Nb": 92.9064,
    "Mo": 95.95,
    "Tc": 98.0,
    "Ru": 101.07,
    "Rh": 102.9055,
    "Pd": 106.42,
    "Ag": 107.8682,
    "Cd": 112.414,
    "In": 114.818,
    "Sn": 118.710,
    "Sb": 121.760,
    "Te": 127.60,
    "I": 126.9045,
    "Xe": 131.293,
    "Cs": 132.9055,
    "Ba": 137.327,
    "La": 138.9055,
    "Ce": 140.116,
    "Pr": 140.9077,
    "Nd": 144.242,
    "Pm": 145.0,
    "Sm": 150.36,
    "Eu": 151.964,
    "Gd": 157.25,
    "Tb": 158.9254,
    "Dy": 162.500,
    "Ho": 164.9303,
    "Er": 167.259,
    "Tm": 168.9342,
    "Yb": 173.045,
    "Lu": 174.9668,
    "Hf": 178.49,
    "Ta": 180.9479,
    "W": 183.84,
    "Re": 186.207,
    "Os": 190.23,
    "Ir": 192.217,
    "Pt": 195.084,
    "Au": 196.9666,
    "Hg": 200.592,
    "Tl": 204.38,
    "Pb": 207.2,
    "Bi": 208.9804,
    "Po": 209.0,
    "At": 210.0,
    "Rn": 222.0,
    "Fr": 223.0,
    "Ra": 226.0,
    "Ac": 227.0,
    "Th": 232.0377,
    "Pa": 231.0359,
    "U": 238.0289,
    "Np": 237.0,
    "Pu": 244.0,
    "Am": 243.0,
    "Cm": 247.0,
    "Bk": 247.0,
    "Cf": 251.0,
    "Es": 252.0,
    "Fm": 257.0,
    "Md": 258.0,
    "No": 259.0,
    "Lr": 262.0,
    "Rf": 267.0,
    "Db": 270.0,
    "Sg": 271.0,
    "Bh": 270.0,
    "Hs": 277.0,
    "Mt": 276.0,
    "Ds": 281.0,
    "Rg": 282.0,
    "Cn": 285.0,
    "Nh": 286.0,
    "Fl": 289.0,
    "Mc": 290.0,
    "Lv": 293.0,
    "Ts": 294.0,
    "Og": 294.0,
}

DEFAULT_RADIUS = 0.8
DEFAULT_VDW_RADIUS = 1.5


def get_color(element_symbol: str) -> list[float]:
    """Return RGB float list for a given element symbol."""
    return CPK_COLORS.get(element_symbol.capitalize(), DEFAULT_COLOR)


def get_radius(element_symbol: str) -> float:
    """Return atomic radius float for a given element symbol."""
    return ATOMIC_RADII.get(element_symbol.capitalize(), DEFAULT_RADIUS)


def resolve_color(color_name: str) -> str:
    """
    Resolve a color name to its hex code if it exists in our dictionary.
    Otherwise, returns the string as-is (assuming it's already a valid hex/rgb string).
    """
    return NAMED_COLORS.get(color_name.strip().lower(), color_name)


def compute_bonds(data: dict, use_pbc: bool = False) -> list[dict]:
    """
    Auto-compute bonds based on atomic radii and periodic boundary conditions
    (if unit_cell is provided).
    """
    positions = data.get("positions", [])
    if not positions:
        return []

    species = data.get("species", [])
    unit_cell = data.get("unit_cell")

    num_atoms = len(positions)
    pos_arr = np.array(positions, dtype=float)

    radii = np.array(
        [
            ATOMIC_RADII.get(str(species[i] if i < len(species) else "").capitalize(), DEFAULT_RADIUS)
            for i in range(num_atoms)
        ]
    )

    bonds = []
    has_pbc = False
    if use_pbc and unit_cell:
        try:
            unit_cell_arr = np.array(unit_cell, dtype=float)
            inv_cell = np.linalg.inv(unit_cell_arr)
            frac_pos = pos_arr @ inv_cell
            has_pbc = True
        except (ValueError, np.linalg.LinAlgError):
            pass

    for i in range(num_atoms):
        rA = radii[i]
        j_indices = np.arange(i + 1, num_atoms)
        if len(j_indices) == 0:
            break

        if has_pbc:
            df = frac_pos[i] - frac_pos[j_indices]
            df -= np.round(df)
            dc = df @ unit_cell_arr
        else:
            dc = pos_arr[i] - pos_arr[j_indices]

        dist = np.linalg.norm(dc, axis=1)

        thresholds = (rA + radii[j_indices]) * 1.3

        connected = np.where((dist > 0.1) & (dist < thresholds))[0]
        for idx in connected:
            j = int(j_indices[idx])
            bonds.append({"source": i, "target": j})

    return bonds


def _center_molecules(
    positions: np.ndarray, molecules: list[list[int]], inv_cell: np.ndarray, unit_cell: np.ndarray
) -> None:
    """Center each molecule in the unit cell in-place."""
    for mol in molecules:
        if not mol:
            continue

        mol_idx = np.array(mol)

        # Calculate centroid of the unwrapped molecule
        centroid = np.mean(positions[mol_idx], axis=0)

        # Shift centroid into the unit cell (0 to 1 in fractional coords)
        cf = centroid @ inv_cell
        shift_f = np.floor(cf)
        shift_c = shift_f @ unit_cell

        positions[mol_idx] -= shift_c


def _unwrap_components(
    num_atoms: int, adj: dict, positions: np.ndarray, inv_cell: np.ndarray, unit_cell: np.ndarray
) -> list[list[int]]:
    """Perform BFS to find connected components and unwrap them."""
    visited = np.zeros(num_atoms, dtype=bool)
    molecules = []

    for i in range(num_atoms):
        if not visited[i]:
            comp = []
            queue = [i]
            visited[i] = True
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for neighbor in adj[curr]:
                    if not visited[neighbor]:
                        visited[neighbor] = True

                        # Unwrap neighbor relative to curr
                        df = (positions[neighbor] - positions[curr]) @ inv_cell
                        df -= np.round(df)
                        positions[neighbor] = positions[curr] + df @ unit_cell

                        queue.append(neighbor)
            molecules.append(comp)

    return molecules


def unwrap_molecules(data: dict) -> dict:
    """
    Unwrap molecules split across periodic boundaries, ensuring their centroids
    are inside the unit cell.
    """
    if "unit_cell" not in data or not data["unit_cell"]:
        return data

    positions = data.get("positions", [])
    if not positions:
        return data

    bonds = data.get("bonds", [])

    try:
        unit_cell = np.array(data["unit_cell"], dtype=float)
        inv_cell = np.linalg.inv(unit_cell)
    except (ValueError, np.linalg.LinAlgError):
        return data

    num_atoms = len(positions)

    # 1. Determine bonds if not provided (to find molecules)
    if not bonds:
        bonds = compute_bonds(data, use_pbc=True)

    adj = {i: [] for i in range(num_atoms)}
    for bond in bonds:
        u, v = bond["source"], bond["target"]
        adj[u].append(v)
        adj[v].append(u)

    # 2. Find connected components (molecules) and unwrap
    new_data = copy.deepcopy(data)
    new_positions = np.array(new_data["positions"], dtype=float)

    molecules = _unwrap_components(num_atoms, adj, new_positions, inv_cell, unit_cell)

    # 3. Center each molecule
    _center_molecules(new_positions, molecules, inv_cell, unit_cell)

    new_data["positions"] = new_positions.tolist()
    return new_data


def compute_extra_data(data: dict) -> dict:
    """
    Compute extra data for a structure and add it to its 'extra_data' dictionary.

    For non-periodic structures:
        - number_of_atoms: total number of atoms
        - atomic_weight: total atomic weight in g/mol

    For periodic structures:
        - density: density in g/cm³
        - volume: unit cell volume in Å³
        - number_of_atoms: total number of atoms in the unit cell
        - a: length of the 'a' cell vector in Å
        - b: length of the 'b' cell vector in Å
        - c: length of the 'c' cell vector in Å
        - alpha: angle between 'b' and 'c' cell vectors in degrees
        - beta: angle between 'a' and 'c' cell vectors in degrees
        - gamma: angle between 'a' and 'b' cell vectors in degrees

    Parameters
    ----------
    data : dict
        A structure dictionary with 'species', 'positions', and optional 'unit_cell'.

    Returns
    -------
    dict
        The updated 'extra_data' dictionary of the structure.
    """
    if not isinstance(data, dict):
        return {}

    if "extra_data" not in data or data["extra_data"] is None or not isinstance(data["extra_data"], dict):
        data["extra_data"] = {}

    species = data.get("species", [])
    positions = data.get("positions", [])
    unit_cell = data.get("unit_cell")

    num_atoms = len(positions) if positions else len(species)
    total_atomic_weight = float(sum(ATOMIC_WEIGHTS.get(str(s).strip().capitalize(), 0.0) for s in species))

    is_periodic = False
    cell_arr = None
    if unit_cell:
        try:
            cell_arr = np.array(unit_cell, dtype=float)
            if cell_arr.shape == (3, 3):
                vol = float(abs(np.linalg.det(cell_arr)))
                if vol > 1e-6:
                    is_periodic = True
        except (ValueError, TypeError, np.linalg.LinAlgError):
            is_periodic = False

    if is_periodic and cell_arr is not None:
        a_len = float(np.linalg.norm(cell_arr[0]))
        b_len = float(np.linalg.norm(cell_arr[1]))
        c_len = float(np.linalg.norm(cell_arr[2]))
        alpha = np.arccos(np.dot(cell_arr[1], cell_arr[2]) / (b_len * c_len)) * 180 / np.pi
        beta = np.arccos(np.dot(cell_arr[0], cell_arr[2]) / (a_len * c_len)) * 180 / np.pi
        gamma = np.arccos(np.dot(cell_arr[0], cell_arr[1]) / (a_len * b_len)) * 180 / np.pi
        volume = float(abs(np.linalg.det(cell_arr)))
        # Density in g/cm³: (mass_g_per_mol) / (volume_A3 * N_A * 1e-24)
        # N_A * 1e-24 = 0.602214076
        density = float(total_atomic_weight / (volume * 0.602214076)) if volume > 0 else 0.0

        data["extra_data"]["density"] = density
        data["extra_data"]["volume"] = volume
        data["extra_data"]["nº atoms"] = int(num_atoms)
        data["extra_data"]["a"] = a_len
        data["extra_data"]["b"] = b_len
        data["extra_data"]["c"] = c_len
        data["extra_data"]["alpha"] = alpha
        data["extra_data"]["beta"] = beta
        data["extra_data"]["gamma"] = gamma
    else:
        data["extra_data"]["nº atoms"] = int(num_atoms)
        data["extra_data"]["atomic weight"] = total_atomic_weight

    return data["extra_data"]


def parse_toml_config(config: dict | str | os.PathLike) -> dict:
    """
    Parse a TOML configuration from a dictionary, a file path (PathLike or str), or a TOML formatted string.

    Parameters
    ----------
    config : dict, str, or os.PathLike
        A dictionary of configuration settings, a path to a TOML file, or a TOML formatted string.

    Returns
    -------
    dict
        Parsed configuration dictionary.
    """
    if isinstance(config, dict):
        return dict(config)

    if isinstance(config, os.PathLike):
        with open(config, "rb") as f:
            return tomllib.load(f)

    if isinstance(config, str):
        try:
            is_file = os.path.isfile(config)
        except (ValueError, OSError):
            is_file = False

        if is_file:
            with open(config, "rb") as f:
                return tomllib.load(f)
        else:
            return tomllib.loads(config)

    raise TypeError(f"Expected dict, str, or os.PathLike for config, got {type(config).__name__}")
