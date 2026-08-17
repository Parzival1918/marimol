from __future__ import annotations

from collections.abc import Callable

import marimo as mo

from .viewer import view_structure

__all__ = ["view_ase", "view_pymatgen", "view_cspy"]


try:
    import ase

    ASE = True
except ImportError:
    ASE = False


def _to_json_compatible(val):
    if hasattr(val, "tolist"):
        return val.tolist()
    if hasattr(val, "item"):
        return val.item()
    if isinstance(val, dict):
        return {k: _to_json_compatible(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_to_json_compatible(v) for v in val]
    return val


def _convert_ase_atoms(atoms: ase.Atoms, extra_data_func: Callable[[ase.Atoms], dict] | None = None) -> dict:
    symbols = atoms.get_chemical_symbols()
    positions = atoms.get_positions()

    cell = atoms.get_cell().tolist()
    if not any(any(val != 0 for val in row) for row in cell):
        cell = None

    extra_data = {}
    if hasattr(atoms, "info") and atoms.info:
        extra_data.update(atoms.info)
    if hasattr(atoms, "calc") and atoms.calc is not None and hasattr(atoms.calc, "results") and atoms.calc.results:
        for k, v in atoms.calc.results.items():
            if k not in extra_data:
                extra_data[k] = v

    if extra_data_func is not None:
        custom_data = extra_data_func(atoms)
        if not isinstance(custom_data, dict):
            raise TypeError(f"extra_data callable must return a dict, got {type(custom_data).__name__}")
        extra_data.update(custom_data)

    data = {
        "positions": positions.tolist(),
        "species": symbols,
        "bonds": [],
        "unit_cell": cell,
    }
    if extra_data:
        data["extra_data"] = {k: _to_json_compatible(v) for k, v in extra_data.items()}

    return data


def view_ase(
    atoms: ase.Atoms | list[ase.Atoms],
    extra_data: Callable[[ase.Atoms], dict] | None = None,
    **kwargs,
) -> mo.ui.anywidget:
    """
    Visualize ASE Atoms or list of Atoms objects. Data stored in the `info` attribute
    and `calc.results` attribute are automatically added to the `extra_data` attribute
    of the data dictionary.

    Parameters
    ----------
    atoms : ase.Atoms | list[ase.Atoms]
        ASE Atoms object or list of ASE Atoms objects to visualize.
    extra_data : Callable[[ase.Atoms], dict], optional
        A callable that accepts a single ASE Atoms object and returns a dictionary of
        extra data to attach to the structure. *(added in v0.3.0)*
    **kwargs
        Additional keyword arguments to pass to :func:`~marimol.viewer.view_structure`.

    Returns
    -------
    marimo.ui.anywidget
        The molecule viewer widget.
    """
    if not ASE:
        raise ImportError("ASE is not installed. Please install it to use this function.")

    if extra_data is not None and not callable(extra_data):
        raise TypeError(f"extra_data must be a callable, got {type(extra_data).__name__}")

    if isinstance(atoms, list):
        data = []
        for frame in atoms:
            data.append(_convert_ase_atoms(frame, extra_data_func=extra_data))
        return view_structure(data, **kwargs)
    else:
        return view_structure(_convert_ase_atoms(atoms, extra_data_func=extra_data), **kwargs)


try:
    from pymatgen.core import Structure

    PYMATGEN = True
except ImportError:
    PYMATGEN = False


def _convert_pmg_structure(structure: Structure, extra_data_func: Callable[[Structure], dict] | None = None) -> dict:
    species = [site.specie.symbol for site in structure.sites]
    positions = [site.coords.tolist() for site in structure.sites]
    cell = structure.lattice.matrix.tolist()

    data = {"positions": positions, "species": species, "bonds": [], "unit_cell": cell}
    extra_data = {}
    if extra_data_func is not None:
        custom_data = extra_data_func(structure)
        if not isinstance(custom_data, dict):
            raise TypeError(f"extra_data callable must return a dict, got {type(custom_data).__name__}")
        extra_data.update(custom_data)

    if extra_data:
        data["extra_data"] = {k: _to_json_compatible(v) for k, v in extra_data.items()}

    return data


def view_pymatgen(
    structure: Structure | list[Structure],
    extra_data: Callable[[Structure], dict] | None = None,
    **kwargs,
) -> mo.ui.anywidget:
    """
    Visualize Pymatgen Structure or list of Structures.

    Parameters
    ----------
    structure : Structure | list[Structure]
        Pymatgen Structure object or list of Pymatgen Structure objects to visualize.
    extra_data : Callable[[Structure], dict], optional
        A callable that accepts a single Pymatgen Structure object and returns a dictionary of
        extra data to attach to the structure. *(added in v0.3.0)*
    **kwargs
        Additional keyword arguments to pass to :func:`~marimol.viewer.view_structure`.

    Returns
    -------
    marimo.ui.anywidget
        The molecule viewer widget.
    """
    if not PYMATGEN:
        raise ImportError("Pymatgen is not installed. Please install it to use this function.")

    if extra_data is not None and not callable(extra_data):
        raise TypeError(f"extra_data must be a callable, got {type(extra_data).__name__}")

    if isinstance(structure, list):
        data = []
        for frag in structure:
            data.append(_convert_pmg_structure(frag, extra_data_func=extra_data))
        return view_structure(data, **kwargs)
    else:
        return view_structure(_convert_pmg_structure(structure, extra_data_func=extra_data), **kwargs)


try:
    from cspy import Crystal, Molecule

    CSPY = True
except ImportError:
    CSPY = False


def _convert_cspy_structure(
    structure: Crystal | Molecule, extra_data_func: Callable[[Crystal | Molecule], dict] | None = None
) -> dict:
    orig_structure = structure
    if isinstance(structure, Crystal):
        structure = structure.as_P1()
        molecules = structure.asym_mols()
    else:
        molecules = [structure]

    positions = []
    species = []
    bonds = []  # list of {"source": int, "target": int}
    initial_indices = 0
    for molecule in molecules:
        positions.extend(molecule.positions.tolist())
        species.extend([e.symbol for e in molecule.elements])
        mol_bonds = molecule.bonds
        if mol_bonds is not None:
            for r, c in mol_bonds.keys():
                bonds.append({"source": int(r) + initial_indices, "target": int(c) + initial_indices})
        initial_indices += len(molecule.positions)

    cell = None
    if isinstance(structure, Crystal):
        cell = structure.unit_cell.lattice.tolist()

    data = {"positions": positions, "species": species, "bonds": bonds, "unit_cell": cell}
    extra_data = {}
    if extra_data_func is not None:
        custom_data = extra_data_func(orig_structure)
        if not isinstance(custom_data, dict):
            raise TypeError(f"extra_data callable must return a dict, got {type(custom_data).__name__}")
        extra_data.update(custom_data)

    if extra_data:
        data["extra_data"] = {k: _to_json_compatible(v) for k, v in extra_data.items()}

    return data


def view_cspy(
    structure: Crystal | Molecule | list[Crystal | Molecule],
    extra_data: Callable[[Crystal | Molecule], dict] | None = None,
    **kwargs,
) -> mo.ui.anywidget:
    """
    Visualize Cspy Crystal or Molecule or list of Crystal or Molecule objects.

    Parameters
    ----------
    structure : Crystal | Molecule | list[Crystal | Molecule]
        Cspy Crystal or Molecule object or list of Cspy Crystal or Molecule objects to visualize.
    extra_data : Callable[[Crystal | Molecule], dict], optional
        A callable that accepts a single Cspy Crystal or Molecule object and returns a dictionary of
        extra data to attach to the structure. *(added in v0.3.0)*
    **kwargs
        Additional keyword arguments to pass to :func:`~marimol.viewer.view_structure`.

    Returns
    -------
    marimo.ui.anywidget
        The molecule viewer widget.
    """
    if not CSPY:
        raise ImportError("mol-cspy is not installed. Please install it to use this function.")

    if extra_data is not None and not callable(extra_data):
        raise TypeError(f"extra_data must be a callable, got {type(extra_data).__name__}")

    if isinstance(structure, list):
        data = []
        for frag in structure:
            data.append(_convert_cspy_structure(frag, extra_data_func=extra_data))
        return view_structure(data, **kwargs)
    else:
        return view_structure(_convert_cspy_structure(structure, extra_data_func=extra_data), **kwargs)
