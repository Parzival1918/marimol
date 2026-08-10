import copy

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
