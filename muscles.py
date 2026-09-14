"""Canonical display names for the bundled exercise-library muscle labels."""
MUSCLES = {"chest": "Pectoralis Major", "lats": "Latissimus Dorsi", "middle back": "Middle Back", "lower back": "Erector Spinae", "shoulders": "Deltoids", "biceps": "Biceps", "triceps": "Triceps", "forearms": "Forearms", "abdominals": "Rectus Abdominis", "obliques": "Obliques", "quads": "Quadriceps", "hamstrings": "Hamstrings", "glutes": "Gluteus Maximus", "calves": "Calves", "traps": "Trapezius"}
def display_muscle(name): return MUSCLES.get(name.lower(), name.title())
