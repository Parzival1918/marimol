# CPK Colors and standard atomic radii (in Angstroms) for visualization

CPK_COLORS = {
    "H": [1.0, 1.0, 1.0],      # White
    "C": [0.56, 0.56, 0.56],   # Light Grey
    "N": [0.19, 0.31, 0.97],   # Blue
    "O": [1.0, 0.05, 0.05],    # Red
    "F": [0.56, 0.88, 0.31],   # Green
    "Cl": [0.12, 0.94, 0.12],  # Green
    "Br": [0.65, 0.16, 0.16],  # Dark Red
    "I": [0.58, 0.0, 0.58],    # Purple
    "S": [1.0, 0.78, 0.20],    # Yellow
    "P": [1.0, 0.50, 0.0],     # Orange
    "B": [1.0, 0.71, 0.71],    # Peach
    "Si": [0.94, 0.78, 0.63],  # Tan
    "Fe": [0.88, 0.40, 0.20],  # Orange-red
    "Cu": [0.78, 0.50, 0.20],  # Copper
    "Ag": [0.75, 0.75, 0.75],  # Silver
    "Au": [1.0, 0.82, 0.14],   # Gold
}

# Default color for unknown elements (Pink)
DEFAULT_COLOR = [1.0, 0.08, 0.58]

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

DEFAULT_RADIUS = 0.8

def get_color(element_symbol: str) -> list[float]:
    """Return RGB float list for a given element symbol."""
    return CPK_COLORS.get(element_symbol.capitalize(), DEFAULT_COLOR)

def get_radius(element_symbol: str) -> float:
    """Return atomic radius float for a given element symbol."""
    return ATOMIC_RADII.get(element_symbol.capitalize(), DEFAULT_RADIUS)

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

def resolve_color(color_name: str) -> str:
    """
    Resolve a color name to its hex code if it exists in our dictionary.
    Otherwise, returns the string as-is (assuming it's already a valid hex/rgb string).
    """
    return NAMED_COLORS.get(color_name.strip().lower(), color_name)
