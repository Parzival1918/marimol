from __future__ import annotations
from .viewer import view_molecule
import marimo as mo


__all__ = ["view_ase", "view_pymatgen"]


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


def view_ase(atoms: "ase.Atoms" | list["ase.Atoms"], **kwargs) -> mo.ui.anywidget:
    """
    Visualize ASE Atoms or list of Atoms objects.

    Parameters
    ----------
    atoms : ase.Atoms | list[ase.Atoms]
        ASE Atoms object or list of ASE Atoms objects to visualize.
    **kwargs
        Additional keyword arguments to pass to :func:`~marimol.viewer.view_molecule`.

    Returns
    -------
    marimo.ui.anywidget
        The molecule viewer widget.
    """
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


def view_pymatgen(structure: "Structure" | list["Structure"], **kwargs) -> mo.ui.anywidget:
    """
    Visualize Pymatgen Structure or list of Structures.

    Parameters
    ----------
    structure : Structure | list[Structure]
        Pymatgen Structure object or list of Pymatgen Structure objects to visualize.
    **kwargs
        Additional keyword arguments to pass to :func:`~marimol.viewer.view_molecule`.

    Returns
    -------
    marimo.ui.anywidget
        The molecule viewer widget.
    """
    if not PYMATGEN:
        raise ImportError("Pymatgen is not installed. Please install it to use this function.")
    
    if isinstance(structure, list):
        data = []
        for frag in structure:
            data.append(_convert_pmg_structure(frag))
        return view_molecule(data, **kwargs)
    else:
        return view_molecule(_convert_pmg_structure(structure), **kwargs)
