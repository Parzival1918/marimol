import importlib.metadata

from .external import view_ase, view_cspy, view_pymatgen
from .utils import compute_extra_data, get_color, get_radius, resolve_color, unwrap_molecules
from .viewer import MoleculeViewerWidget, view_structure

__version__ = importlib.metadata.version("marimol")

__all__ = [
    "__version__",
    "view_structure",
    "MoleculeViewerWidget",
    "get_color",
    "get_radius",
    "resolve_color",
    "unwrap_molecules",
    "compute_extra_data",
    "view_ase",
    "view_pymatgen",
    "view_cspy",
]
