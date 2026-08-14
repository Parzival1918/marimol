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
