import importlib.metadata

from .controls import MoleculeViewerControls, controls, create_controls, get_viewer_config
from .external import view_ase, view_cspy, view_pymatgen
from .utils import (
    compute_extra_data,
    dict_to_toml,
    get_color,
    get_radius,
    parse_toml_config,
    process_vectors,
    resolve_color,
    unwrap_molecules,
)
from .viewer import MoleculeViewerWidget, view_structure

__version__ = importlib.metadata.version("marimol")

__all__ = [
    "__version__",
    "view_structure",
    "MoleculeViewerWidget",
    "MoleculeViewerControls",
    "create_controls",
    "controls",
    "get_viewer_config",
    "dict_to_toml",
    "get_color",
    "get_radius",
    "resolve_color",
    "unwrap_molecules",
    "compute_extra_data",
    "process_vectors",
    "parse_toml_config",
    "view_ase",
    "view_pymatgen",
    "view_cspy",
]
