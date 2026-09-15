"""Canonical muscle names and anatomy regions for the local exercise library."""

MUSCLES = {"chest": "Pectoralis Major", "lats": "Latissimus Dorsi", "middle back": "Middle Back", "lower back": "Erector Spinae", "shoulders": "Deltoids", "biceps": "Biceps", "triceps": "Triceps", "forearms": "Forearms", "abdominals": "Rectus Abdominis", "obliques": "Obliques", "quads": "Quadriceps", "hamstrings": "Hamstrings", "glutes": "Gluteus Maximus", "calves": "Calves", "traps": "Trapezius"}

# Dataset label -> reusable SVG region. Keep this mapping separate from the diagram
# so new exercise-library labels can be supported without redrawing anatomy artwork.
MUSCLE_REGIONS = {
    "chest": ("chest",), "shoulders": ("shoulders",), "biceps": ("biceps",),
    "triceps": ("triceps",), "forearms": ("forearms",), "abdominals": ("abs",),
    "obliques": ("obliques",), "quads": ("quads",), "hamstrings": ("hamstrings",),
    "glutes": ("glutes",), "calves": ("calves",), "lats": ("lats",),
    "middle back": ("middle_back",), "lower back": ("lower_back",), "traps": ("traps",),
}

def normalize_muscle(name):
    """Normalize a bundled label or common synonym to its supported dataset label."""
    value = (name or "").lower().strip()
    aliases = {"pectorals": "chest", "deltoids": "shoulders", "quadriceps": "quads", "gluteals": "glutes", "latissimus dorsi": "lats", "abs": "abdominals", "erectors": "lower back", "gastrocnemius": "calves"}
    return aliases.get(value, value)

def diagram_regions(muscles):
    return tuple(region for muscle in muscles for region in MUSCLE_REGIONS.get(normalize_muscle(muscle), ()))

def display_muscle(name): return MUSCLES.get(normalize_muscle(name), (name or "").title())
