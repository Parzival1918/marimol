from __future__ import annotations
from .viewer import view_molecule

try:
    import ase
    ASE = True
except ImportError:
    ASE = False

def _convert_ase_atoms(atoms: "ase.Atoms") -> dict:
    symbols = atoms.get_chemical_symbols()
    positions = atoms.get_positions()
    
    cell = atoms.get_cell().tolist()
    if not any(any(val != 0 for val in row) for row in cell):
        cell = None

    return {
        "positions": positions.tolist(),
        "species": symbols,
        "bonds": [],
        "unit_cell": cell
    }

def view_ase(atoms: "ase.Atoms" | list["ase.Atoms"], **kwargs):
    if not ASE:
        raise ImportError("ASE is not installed. Please install it to use this function.")
    
    if isinstance(atoms, list):
        data = []
        for frame in atoms:
            data.append(_convert_ase_atoms(frame))
        return view_molecule(data, **kwargs)
    else:
        return view_molecule(_convert_ase_atoms(atoms), **kwargs)

try:
    from pymatgen.core import Structure
    PYMATGEN = True
except ImportError:
    PYMATGEN = False

def _convert_pmg_structure(structure: "Structure") -> dict:
    species = [site.specie.symbol for site in structure.sites]
    positions = [site.coords.tolist() for site in structure.sites]
    cell = structure.lattice.matrix.tolist()

    return {
        "positions": positions,
        "species": species,
        "bonds": [],
        "unit_cell": cell
    }

def view_pymatgen(structure: "Structure" | list["Structure"], **kwargs):
    if not PYMATGEN:
        raise ImportError("Pymatgen is not installed. Please install it to use this function.")
    
    if isinstance(structure, list):
        data = []
        for frag in structure:
            data.append(_convert_pmg_structure(frag))
        return view_molecule(data, **kwargs)
    else:
        return view_molecule(_convert_pmg_structure(structure), **kwargs)