import numpy as np
from cspy import Molecule
from cspy.crystal.generate_crystal import CrystalGenerator

from marimol.external import _convert_cspy_structure
from marimol.utils import compute_bonds, unwrap_molecules


def test_unwrap_cspy_methane_crystals():
    xyz = """5
methane
C 2.629 2.629 2.629
H 2.000 3.258 2.000
H 3.258 3.258 3.258
H 2.000 2.000 3.258
H 3.258 2.000 2.000"""

    mol = Molecule.from_xyz_string(xyz)
    mol.guess_bonds()

    generator = CrystalGenerator([mol], space_group=1)
    valid_crystals = []
    for seed in range(1, 1000):
        c = generator.generate(seed)
        if c is not None:
            valid_crystals.append(c)
            if len(valid_crystals) >= 3:
                break

    assert len(valid_crystals) >= 3

    for crystal in valid_crystals:
        data = _convert_cspy_structure(crystal)
        unwrapped = unwrap_molecules(data)

        orig_pos = np.array(data["positions"])
        unwrapped_pos = np.array(unwrapped["positions"])

        # Every C-H bond distance in the unwrapped molecule must equal the original bond distance ~1.089 Å
        for h in range(1, 5):
            d_orig = np.linalg.norm(orig_pos[h] - orig_pos[0])
            d_unwrapped = np.linalg.norm(unwrapped_pos[h] - unwrapped_pos[0])
            assert np.isclose(d_orig, d_unwrapped, atol=1e-4)


def test_unwrap_split_molecule():
    # Molecule with bond split across PBC: atom 0 at [0.1, 0.1, 0.1], atom 1 at [9.9, 0.1, 0.1]
    # in a cubic cell with a = 10.0. Real bond length is 0.2 Å across boundary.
    data = {
        "positions": [[0.1, 0.1, 0.1], [9.9, 0.1, 0.1]],
        "species": ["H", "H"],
        "unit_cell": [[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]],
    }
    bonds_no_pbc = compute_bonds(data, use_pbc=False)
    assert len(bonds_no_pbc) == 0

    bonds = compute_bonds(data, use_pbc=True)
    assert len(bonds) == 1

    unwrapped = unwrap_molecules(data)
    pos = np.array(unwrapped["positions"])
    # The bond distance in Cartesian space should now be 0.2 Å
    d = np.linalg.norm(pos[0] - pos[1])
    assert np.isclose(d, 0.2, atol=1e-4)


def test_view_structure_unwrap_molecules_false_vs_true():
    from marimol import view_structure

    data = {
        "positions": [[0.1, 0.1, 0.1], [9.9, 0.1, 0.1]],
        "species": ["H", "H"],
        "unit_cell": [[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]],
    }

    # When unwrap_molecules=False, no PBC bonds should be computed across the cell
    widget_false = view_structure(data, unwrap_molecules=False)
    assert widget_false.widget.data[0]["bonds"] == []

    # When unwrap_molecules=True, molecules are unwrapped and bonds are computed
    widget_true = view_structure(data, unwrap_molecules=True)
    assert len(widget_true.widget.data[0]["bonds"]) == 1
    assert widget_true.widget.data[0]["bonds"][0] == {"source": 0, "target": 1}


def test_view_ase_unwrap_molecules_false_vs_true():
    from ase import Atoms

    from marimol import view_ase

    atoms = Atoms(
        symbols=["H", "H"],
        positions=[[0.1, 0.1, 0.1], [9.9, 0.1, 0.1]],
        cell=[[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]],
        pbc=True,
    )

    # When unwrap_molecules=False (default), bonds across PBC must not be computed
    widget_default = view_ase(atoms)
    assert widget_default.widget.data[0]["bonds"] == []

    widget_false = view_ase(atoms, unwrap_molecules=False)
    assert widget_false.widget.data[0]["bonds"] == []

    # When unwrap_molecules=True, bonds are computed and atoms are unwrapped
    widget_true = view_ase(atoms, unwrap_molecules=True)
    assert len(widget_true.widget.data[0]["bonds"]) == 1
    assert widget_true.widget.data[0]["bonds"][0] == {"source": 0, "target": 1}
