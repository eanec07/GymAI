"""Small, dependency-free English/Spanish presentation helpers for SYLRIX."""

SUPPORTED_LANGUAGES = {"en", "es"}

TRANSLATIONS = {
    "en": {},
    "es": {
        "English": "English", "Español": "Español", "Home": "Inicio", "Log in": "Iniciar sesión",
        "Log out": "Cerrar sesión", "Get started": "Comenzar", "Dashboard": "Panel",
        "Workout": "Entrenamiento", "Exercises": "Ejercicios", "Coach": "Coach", "Nutrition": "Nutrición",
        "Progress": "Progreso", "Profile": "Perfil", "Readiness": "Preparación", "Steps": "Pasos",
        "History": "Historial", "Save": "Guardar", "Search": "Buscar", "Back to plan": "Volver al plan",
        "Create account": "Crear cuenta", "Sign in to SYLRIX.": "Inicia sesión en SYLRIX.",
        "Welcome back": "Bienvenido de nuevo", "Username or email": "Usuario o correo electrónico",
        "Password": "Contraseña", "New here?": "¿Eres nuevo?", "Build your account.": "Crea tu cuenta.",
        "Workout complete": "Entrenamiento completado", "Session saved.": "Sesión guardada.",
        "Rest timer": "Temporizador de descanso", "Pause": "Pausar", "Reset": "Reiniciar",
        "Finish workout": "Finalizar entrenamiento", "Exercise": "Ejercicio", "Set": "Serie",
        "Weight": "Peso", "Reps": "Repeticiones", "Target": "Objetivo", "Previous": "Anterior",
        "Saved": "Guardado", "Warm-up": "Calentamiento", "Exercise info": "Información del ejercicio",
        "Connection required": "Se requiere conexión", "You’re offline.": "No tienes conexión.",
        "Try again": "Intentar de nuevo", "Create your own SYLRIX.FIT account": "Crea tu propia cuenta SYLRIX.FIT",
        "Shared workout": "Entrenamiento compartido", "Workout unavailable": "Entrenamiento no disponible",
        "This workout link is unavailable or has been revoked.": "Este enlace de entrenamiento no está disponible o fue revocado.",
        "Share workout": "Compartir entrenamiento", "Show QR": "Mostrar QR", "Copy link": "Copiar enlace",
        "Revoke link": "Revocar enlace", "Regenerate link": "Regenerar enlace", "Active link": "Enlace activo",
        "No account is required to view this workout.": "No necesitas una cuenta para ver este entrenamiento.",
        "Primary muscles": "Músculos principales", "Supporting muscles": "Músculos secundarios",
        "Equipment": "Equipo", "Instructions": "Instrucciones", "Workout": "Entrenamiento",
        "Available": "Disponible", "Unavailable": "No disponible",
    },
}

EXERCISE_TRANSLATIONS = {
    "Bench Press": "Press de banca", "Bench Press - Powerlifting": "Press de banca",
    "Squat": "Sentadilla", "Back Squat": "Sentadilla trasera", "Deadlift": "Peso muerto",
    "Pull-Up": "Dominada", "Push-Up": "Flexión", "Dumbbell Row": "Remo con mancuerna",
    "Barbell Row": "Remo con barra", "Overhead Press": "Press militar",
    "Romanian Deadlift": "Peso muerto rumano", "Bulgarian Split Squat": "Sentadilla búlgara",
    "Lat Pulldown": "Jalón al pecho", "Dips": "Fondos", "Plank": "Plancha",
}

MUSCLE_TRANSLATIONS = {
    "chest": "pecho", "back": "espalda", "lats": "dorsales", "shoulders": "hombros",
    "biceps": "bíceps", "triceps": "tríceps", "quadriceps": "cuádriceps", "hamstrings": "isquiotibiales",
    "glutes": "glúteos", "calves": "pantorrillas", "abdominals": "abdominales", "forearms": "antebrazos",
}


def normalize_language(value):
    return value if value in SUPPORTED_LANGUAGES else "en"


def translate(text, language="en"):
    """Return a presentation string; unknown text safely remains English."""
    return TRANSLATIONS.get(normalize_language(language), {}).get(text, text)


def display_exercise(name, language="en"):
    if normalize_language(language) != "es":
        return name
    return EXERCISE_TRANSLATIONS.get(name, name)


def display_muscle_localized(name, language="en"):
    if normalize_language(language) != "es":
        return name
    return MUSCLE_TRANSLATIONS.get(name.lower(), name)
