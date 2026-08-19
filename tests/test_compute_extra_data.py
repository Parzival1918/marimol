import math

import pytest

from marimol import view_structure
from marimol.utils import ATOMIC_WEIGHTS, compute_extra_data


def test_atomic_weights_table():
    assert "H" in ATOMIC_WEIGHTS
    assert ATOMIC_WEIGHTS["H"] == pytest.approx(1.008)
    assert ATOMIC_WEIGHTS["C"] == pytest.approx(12.011)
    assert ATOMIC_WEIGHTS["O"] == pytest.approx(15.999)
    assert ATOMIC_WEIGHTS["Cu"] == pytest.approx(63.546)
    assert len(ATOMIC_WEIGHTS) == 118


def test_compute_extra_data_non_periodic():
    # Water molecule (H2O)
    data = {
        "positions": [
            [0.0, 0.0, 0.0],
            [0.757, 0.586, 0.0],
            [-0.757, 0.586, 0.0],
        ],
        "species": ["O", "H", "H"],
    }

    extra = compute_extra_data(data)
    assert extra["nº atoms"] == 3
    assert extra["atomic weight"] == pytest.approx(15.999 + 2 * 1.008)
    assert "density" not in extra
    assert "volume" not in extra
    assert "a" not in extra
    assert data["extra_data"] == extra


def test_compute_extra_data_non_periodic_preserves_existing():
    data = {
        "positions": [[0.0, 0.0, 0.0]],
        "species": ["C"],
        "extra_data": {"user_property": 42},
    }

    extra = compute_extra_data(data)
    assert extra["nº atoms"] == 1
    assert extra["atomic weight"] == pytest.approx(12.011)
    assert extra["user_property"] == 42


def test_compute_extra_data_periodic_orthorhombic():
    # Periodic orthorhombic cell
    cell = [
        [3.0, 0.0, 0.0],
        [0.0, 4.0, 0.0],
        [0.0, 0.0, 5.0],
    ]
    data = {
        "positions": [
            [0.0, 0.0, 0.0],
            [1.5, 2.0, 2.5],
        ],
        "species": ["Cu", "Cu"],
        "unit_cell": cell,
    }

    extra = compute_extra_data(data)
    assert extra["nº atoms"] == 2
    assert extra["a"] == pytest.approx(3.0)
    assert extra["b"] == pytest.approx(4.0)
    assert extra["c"] == pytest.approx(5.0)
    assert extra["volume"] == pytest.approx(60.0)

    # Expected density: (2 * 63.546) / (60.0 * 0.602214076)
    expected_density = (2 * 63.546) / (60.0 * 0.602214076)
    assert extra["density"] == pytest.approx(expected_density)
    assert "atomic weight" not in extra


def test_compute_extra_data_periodic_triclinic():
    # Non-orthogonal unit cell
    cell = [
        [2.0, 1.0, 0.0],
        [0.0, 3.0, 0.0],
        [0.0, 0.0, 4.0],
    ]
    data = {
        "positions": [[0.0, 0.0, 0.0]],
        "species": ["Fe"],
        "unit_cell": cell,
    }

    extra = compute_extra_data(data)
    assert extra["nº atoms"] == 1
    assert extra["a"] == pytest.approx(math.sqrt(2**2 + 1**2))
    assert extra["b"] == pytest.approx(3.0)
    assert extra["c"] == pytest.approx(4.0)
    assert extra["volume"] == pytest.approx(24.0)
    expected_density = 55.845 / (24.0 * 0.602214076)
    assert extra["density"] == pytest.approx(expected_density)


def test_compute_extra_data_zero_cell():
    # Zero or degenerate cell should be treated as non-periodic
    data = {
        "positions": [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]],
        "species": ["N", "N"],
        "unit_cell": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
    }
    extra = compute_extra_data(data)
    assert extra["nº atoms"] == 2
    assert extra["atomic weight"] == pytest.approx(28.014)
    assert "density" not in extra


def test_compute_extra_data_case_insensitive_species():
    data = {
        "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "species": ["cu", "CL"],
    }
    extra = compute_extra_data(data)
    assert extra["atomic weight"] == pytest.approx(63.546 + 35.45)


def test_view_structure_compute_extra_data_false():
    data = {
        "positions": [[0.0, 0.0, 0.0]],
        "species": ["C"],
    }
    view_structure(data, compute_extra_data=False)
    # When compute_extra_data is False, extra_data is not automatically created
    assert "extra_data" not in data


def test_view_structure_compute_extra_data_true_single():
    data = {
        "positions": [[0.0, 0.0, 0.0]],
        "species": ["C"],
    }
    view_structure(data, compute_extra_data=True)
    assert "extra_data" in data
    assert data["extra_data"]["nº atoms"] == 1
    assert data["extra_data"]["atomic weight"] == pytest.approx(12.011)


def test_view_structure_compute_extra_data_true_trajectory():
    frames = [
        {
            "positions": [[0.0, 0.0, 0.0]],
            "species": ["H"],
        },
        {
            "positions": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            "species": ["H", "H"],
            "unit_cell": [[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 2.0]],
        },
    ]
    view_structure(frames, compute_extra_data=True)
    assert frames[0]["extra_data"]["nº atoms"] == 1
    assert frames[0]["extra_data"]["atomic weight"] == pytest.approx(1.008)

    assert frames[1]["extra_data"]["nº atoms"] == 2
    assert frames[1]["extra_data"]["volume"] == pytest.approx(8.0)
    assert frames[1]["extra_data"]["a"] == pytest.approx(2.0)
    assert frames[1]["extra_data"]["b"] == pytest.approx(2.0)
    assert frames[1]["extra_data"]["c"] == pytest.approx(2.0)


def test_view_ase_with_compute_extra_data():
    from ase.build import bulk, molecule

    from marimol import view_ase

    mol = molecule("H2O")
    widget_mol = view_ase(mol, compute_extra_data=True)
    # Check that widget got data with extra_data
    frame_data = widget_mol.widget.data[0]
    assert frame_data["extra_data"]["nº atoms"] == 3
    assert frame_data["extra_data"]["atomic weight"] == pytest.approx(18.015)

    crys = bulk("Cu", "fcc", a=3.6)
    widget_crys = view_ase(crys, compute_extra_data=True)
    crys_frame = widget_crys.widget.data[0]
    assert crys_frame["extra_data"]["nº atoms"] == 1
    assert "density" in crys_frame["extra_data"]
    assert "volume" in crys_frame["extra_data"]
    assert "a" in crys_frame["extra_data"]
    assert "b" in crys_frame["extra_data"]
    assert "c" in crys_frame["extra_data"]


def test_view_pymatgen_with_compute_extra_data():
    from pymatgen.core import Lattice, Structure

    from marimol import view_pymatgen

    lattice = Lattice.cubic(3.0)
    structure = Structure(lattice, ["Cs", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])
    widget = view_pymatgen(structure, compute_extra_data=True)
    frame = widget.widget.data[0]
    assert frame["extra_data"]["nº atoms"] == 2
    assert frame["extra_data"]["volume"] == pytest.approx(27.0)
    assert frame["extra_data"]["a"] == pytest.approx(3.0)
    assert frame["extra_data"]["b"] == pytest.approx(3.0)
    assert frame["extra_data"]["c"] == pytest.approx(3.0)
    assert "density" in frame["extra_data"]


def test_compute_extra_data_preserves_clashing_keys():
    # Periodic structure with pre-existing clashing keys
    cell = [
        [3.0, 0.0, 0.0],
        [0.0, 4.0, 0.0],
        [0.0, 0.0, 5.0],
    ]
    data = {
        "positions": [
            [0.0, 0.0, 0.0],
            [1.5, 2.0, 2.5],
        ],
        "species": ["Cu", "Cu"],
        "unit_cell": cell,
        "extra_data": {
            "density": 99.9,
            "volume": 123.4,
            "custom_field": "hello",
        },
    }

    extra = compute_extra_data(data)
    # Custom values should be preserved
    assert extra["density"] == 99.9
    assert extra["volume"] == 123.4
    assert extra["custom_field"] == "hello"
    # Missing default keys should be computed
    assert extra["nº atoms"] == 2
    assert extra["a"] == pytest.approx(3.0)
    assert extra["b"] == pytest.approx(4.0)
    assert extra["c"] == pytest.approx(5.0)


def test_view_ase_custom_extra_data():
    from ase.build import bulk, molecule

    from marimol import view_ase

    mol = molecule("H2O")

    def custom_calc_mol(atoms):
        return {
            "formula": str(atoms.symbols),
            "custom_charge": 0.0,
            "center_of_mass": atoms.get_center_of_mass(),
        }

    widget_mol = view_ase(mol, extra_data=custom_calc_mol)
    frame_data = widget_mol.widget.data[0]
    assert frame_data["extra_data"]["formula"] == "OH2"
    assert frame_data["extra_data"]["custom_charge"] == 0.0
    assert isinstance(frame_data["extra_data"]["center_of_mass"], list)
    assert len(frame_data["extra_data"]["center_of_mass"]) == 3

    # Test trajectory of Atoms with extra_data callable
    crys1 = bulk("Cu", "fcc", a=3.6)
    crys2 = bulk("Cu", "fcc", a=3.8)

    def custom_calc_traj(atoms):
        return {
            "cell_a": float(atoms.cell.lengths()[0]),
            "num_atoms": len(atoms),
        }

    widget_traj = view_ase([crys1, crys2], extra_data=custom_calc_traj)
    frames = widget_traj.widget.data
    assert len(frames) == 2
    assert frames[0]["extra_data"]["cell_a"] == pytest.approx(3.6 / math.sqrt(2))
    assert frames[0]["extra_data"]["num_atoms"] == 1
    assert frames[1]["extra_data"]["cell_a"] == pytest.approx(3.8 / math.sqrt(2))
    assert frames[1]["extra_data"]["num_atoms"] == 1


def test_view_ase_custom_extra_data_with_compute_extra_data():
    from ase.build import bulk

    from marimol import view_ase

    crys = bulk("Cu", "fcc", a=3.6)

    # Callable provides a clashing 'volume' and a custom property
    def custom_calc(atoms):
        return {
            "volume": 999.0,
            "my_tag": "test_tag",
        }

    widget = view_ase(crys, extra_data=custom_calc, compute_extra_data=True)
    frame = widget.widget.data[0]
    # Clashing user value should take precedence over computed volume
    assert frame["extra_data"]["volume"] == 999.0
    assert frame["extra_data"]["my_tag"] == "test_tag"
    # Other default extra data should be computed and populated
    assert frame["extra_data"]["nº atoms"] == 1
    assert frame["extra_data"]["a"] == pytest.approx(3.6 / math.sqrt(2))
    assert "density" in frame["extra_data"]


def test_view_ase_does_not_auto_include_info_or_calc():
    from ase import Atoms
    from ase.calculators.singlepoint import SinglePointCalculator

    from marimol import view_ase

    atoms = Atoms("H2O", positions=[[0, 0, 0], [0, 0, 1], [0, 1, 0]])
    atoms.info["energy"] = -10.5
    calc = SinglePointCalculator(atoms, energy=-10.5, forces=[[0, 0, 0], [0, 0, 0], [0, 0, 0]])
    atoms.calc = calc

    widget = view_ase(atoms)
    frame = widget.widget.data[0]
    assert "extra_data" not in frame


def test_view_pymatgen_custom_extra_data():
    from pymatgen.core import Lattice, Structure

    from marimol import view_pymatgen

    lattice = Lattice.cubic(3.0)
    structure1 = Structure(lattice, ["Cs", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])
    structure2 = Structure(Lattice.cubic(4.0), ["Cs", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])

    def custom_calc_pmg(struct):
        return {
            "formula": struct.composition.reduced_formula,
            "custom_density": float(struct.density),
        }

    # Single structure
    widget = view_pymatgen(structure1, extra_data=custom_calc_pmg)
    frame = widget.widget.data[0]
    assert frame["extra_data"]["formula"] == "CsCl"
    assert frame["extra_data"]["custom_density"] == pytest.approx(float(structure1.density))

    # Trajectory
    widget_traj = view_pymatgen([structure1, structure2], extra_data=custom_calc_pmg)
    assert len(widget_traj.widget.data) == 2
    assert widget_traj.widget.data[0]["extra_data"]["formula"] == "CsCl"
    assert widget_traj.widget.data[1]["extra_data"]["formula"] == "CsCl"
    assert widget_traj.widget.data[0]["extra_data"]["custom_density"] == pytest.approx(float(structure1.density))
    assert widget_traj.widget.data[1]["extra_data"]["custom_density"] == pytest.approx(float(structure2.density))


def test_view_cspy_custom_extra_data():
    pytest.importorskip("cspy")
    import numpy as np
    from cspy import Molecule

    from marimol import view_cspy

    mol1 = Molecule.from_arrays(
        elements=["O", "H", "H"],
        positions=np.array([[0.0, 0.0, 0.0], [0.757, 0.586, 0.0], [-0.757, 0.586, 0.0]]),
    )
    mol2 = Molecule.from_arrays(
        elements=["C", "O"],
        positions=np.array([[0.0, 0.0, 0.0], [1.13, 0.0, 0.0]]),
    )

    def custom_cspy_data(m):
        return {
            "num_elements": len(m.elements),
            "natoms": len(m.positions),
        }

    # Single molecule
    widget = view_cspy(mol1, extra_data=custom_cspy_data)
    frame = widget.widget.data[0]
    assert frame["extra_data"]["num_elements"] == 3
    assert frame["extra_data"]["natoms"] == 3

    # Trajectory / list of molecules
    widget_traj = view_cspy([mol1, mol2], extra_data=custom_cspy_data)
    assert len(widget_traj.widget.data) == 2
    assert widget_traj.widget.data[0]["extra_data"]["natoms"] == 3
    assert widget_traj.widget.data[1]["extra_data"]["natoms"] == 2

    # Crystal with extra_data callable
    crystal = mol1.to_crystal(vacuum=10)

    def custom_crystal_data(c):
        return {
            "spacegroup": "P1",
            "asym_mols": len(c.asym_mols()),
        }

    widget_crys = view_cspy(crystal, extra_data=custom_crystal_data)
    crys_frame = widget_crys.widget.data[0]
    assert crys_frame["extra_data"]["spacegroup"] == "P1"
    assert crys_frame["extra_data"]["asym_mols"] == 1


def test_external_extra_data_invalid_types():
    from ase.build import molecule
    from pymatgen.core import Lattice, Structure

    from marimol import view_ase, view_cspy, view_pymatgen

    mol = molecule("H2O")

    # Non-callable extra_data argument
    with pytest.raises(TypeError, match="extra_data must be a callable"):
        view_ase(mol, extra_data="not_a_callable")

    with pytest.raises(TypeError, match="extra_data must be a callable"):
        view_pymatgen(Structure(Lattice.cubic(3.0), ["C"], [[0, 0, 0]]), extra_data=12345)

    from marimol.external import CSPY

    if CSPY:
        with pytest.raises(TypeError, match="extra_data must be a callable"):
            view_cspy(mol, extra_data=[])
    else:
        with pytest.raises(ImportError, match="mol-cspy is not installed"):
            view_cspy(mol, extra_data=[])

    # Callable returning non-dict
    with pytest.raises(TypeError, match="extra_data callable must return a dict"):
        view_ase(mol, extra_data=lambda x: "not_a_dict")

    with pytest.raises(TypeError, match="extra_data callable must return a dict"):
        view_pymatgen(Structure(Lattice.cubic(3.0), ["C"], [[0, 0, 0]]), extra_data=lambda x: [1, 2, 3])
