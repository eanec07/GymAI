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
    "Barbell Bench Press - Medium Grip": "Press de banca con barra, agarre medio",
    "Bench Press": "Press de banca", "Bench Press - Powerlifting": "Press de banca",
    "Squat": "Sentadilla", "Back Squat": "Sentadilla trasera", "Deadlift": "Peso muerto",
    "Pull-Up": "Dominada", "Push-Up": "Flexión", "Dumbbell Row": "Remo con mancuerna",
    "Barbell Row": "Remo con barra", "Overhead Press": "Press militar",
    "Romanian Deadlift": "Peso muerto rumano", "Bulgarian Split Squat": "Sentadilla búlgara",
    "Lat Pulldown": "Jalón al pecho", "Dips": "Fondos", "Plank": "Plancha",
}

# The bundled source instructions remain canonical English data.  This map is
# deliberately additive: untranslated entries are identified to the athlete
# instead of being machine-translated or silently presented as Spanish.
INSTRUCTION_TRANSLATIONS = {
    "Lie back on a flat bench. Using a medium width grip (a grip that creates a 90-degree angle in the middle of the movement between the forearms and the upper arms), lift the bar from the rack and hold it straight over you with your arms locked. This will be your starting position.": "Túmbate en un banco plano. Con un agarre medio, saca la barra del soporte y sosténla sobre ti con los brazos extendidos. Esta es la posición inicial.",
    "From the starting position, breathe in and begin coming down slowly until the bar touches your middle chest.": "Desde la posición inicial, inhala y baja lentamente hasta que la barra toque la parte media del pecho.",
    "After a brief pause, push the bar back to the starting position as you breathe out. Focus on pushing the bar using your chest muscles. Lock your arms and squeeze your chest in the contracted position at the top of the motion, hold for a second and then start coming down slowly again. Tip: Ideally, lowering the weight should take about twice as long as raising it.": "Tras una breve pausa, empuja la barra de vuelta a la posición inicial al exhalar. Concéntrate en usar el pecho; bloquea los brazos y aprieta el pecho arriba. Baja con control.",
    "Repeat the movement for the prescribed amount of repetitions.": "Repite el movimiento con el número de repeticiones indicado.",
    "When you are done, place the bar back in the rack.": "Al terminar, vuelve a colocar la barra en el soporte.",
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
    translated = EXERCISE_TRANSLATIONS.get(name)
    if translated:
        return translated
    replacements = (("Barbell", "Barra"), ("Dumbbell", "Mancuerna"), ("Cable", "Cable"), ("Machine", "Máquina"), ("Curl", "Curl"), ("Press", "Press"), ("Row", "Remo"), ("Raise", "Elevación"), ("Extension", "Extensión"), ("Leg", "Pierna"), ("Seated", "Sentado"), ("Standing", "De pie"))
    value = name
    for english, spanish in replacements:
        value = value.replace(english, spanish)
    return value


def display_muscle_localized(name, language="en"):
    if normalize_language(language) != "es":
        return name
    return MUSCLE_TRANSLATIONS.get(name.lower(), name)


def display_instruction(instruction, language="en"):
    """Present reviewed Spanish instructions without mutating source exercise data."""
    if normalize_language(language) != "es":
        return instruction
    return INSTRUCTION_TRANSLATIONS.get(instruction, "La traducción de estas instrucciones aún no está disponible.")


HTML_TRANSLATIONS = {
    "Step 1 / Build your profile": "Paso 1 / Crea tu perfil", "Your goals don’t need to fit in a box.": "Tus objetivos no tienen que caber en una sola categoría.", "Start with the basics. Your selected training path adds only the questions that matter for that path.": "Comienza con lo básico. Tu ruta de entrenamiento añade solo las preguntas relevantes.",
    "Core profile": "Perfil básico", "Name": "Nombre", "Age": "Edad", "Sex": "Sexo", "Male": "Hombre", "Female": "Mujer", "Height (in)": "Estatura (pulg)", "Training basics": "Bases del entrenamiento", "Main goal": "Objetivo principal", "Build muscle": "Ganar músculo", "Lose fat": "Perder grasa", "Build strength": "Ganar fuerza", "Maintain or recomposition": "Mantener o recomponer", "Build endurance": "Mejorar resistencia", "Training days/week": "Días de entrenamiento/semana", "Training path": "Ruta de entrenamiento", "Choose later": "Elegir después", "Equipment access": "Acceso a equipo", "Dumbbells": "Mancuernas", "Barbell and rack": "Barra y rack", "Bodyweight only": "Solo peso corporal", "Other / mixed equipment": "Otro / equipo mixto", "Time per workout": "Tiempo por entrenamiento", "About 30 minutes": "Aproximadamente 30 minutos", "About 45 minutes": "Aproximadamente 45 minutos", "About 60 minutes": "Aproximadamente 60 minutos", "75+ minutes": "Más de 75 minutos", "What do you want to achieve?": "¿Qué quieres lograr?", "Other equipment you have": "Otro equipo que tienes", "Optional preferences": "Preferencias opcionales", "Favorite exercises": "Ejercicios favoritos", "Exercises to avoid": "Ejercicios que deseas evitar", "Injuries or limitations": "Lesiones o limitaciones", "Create my plan": "Crear mi plan",
    "Edit profile": "Editar perfil", "Display name": "Nombre visible", "Current weight (lb)": "Peso actual (lb)", "Goal weight (lb)": "Peso objetivo (lb)", "Primary goal": "Objetivo principal", "Training style": "Estilo de entrenamiento", "Experience": "Experiencia", "Days per week": "Días por semana", "Session length (minutes)": "Duración de sesión (minutos)", "Available equipment": "Equipo disponible", "Save profile": "Guardar perfil", "Reset setup": "Reiniciar configuración",
    "Daily check-in": "Registro diario", "How are you feeling today?": "¿Cómo te sientes hoy?", "Sleep hours": "Horas de sueño", "Sleep quality": "Calidad del sueño", "Energy": "Energía", "Soreness": "Dolor muscular", "Stress": "Estrés", "Motivation": "Motivación", "Anything relevant?": "¿Algo relevante?", "Update check-in": "Actualizar registro", "Save check-in": "Guardar registro", "Today’s readiness": "Preparación de hoy", "Your result": "Tu resultado", "Ready when you are.": "Listo cuando tú lo estés.", "Last seven days": "Últimos siete días",
    "Daily nutrition": "Nutrición diaria", "Calories": "Calorías", "Carbs": "Carbohidratos", "Fat": "Grasas", "Fiber": "Fibra", "Add food": "Agregar comida", "Food": "Alimento", "Serving": "Porción", "Recent foods": "Alimentos recientes", "No food entries yet.": "Aún no hay registros de alimentos.", "Edit food": "Editar alimento", "Delete food": "Eliminar alimento", "Food entry saved.": "Registro de alimento guardado.",
    "Track the work, not guesses.": "Registra el trabajo, no las suposiciones.", "Body-weight trend": "Tendencia de peso corporal", "Log body weight": "Registrar peso corporal", "Date": "Fecha", "Weight entries": "Registros de peso", "No body-weight entries yet.": "Aún no hay registros de peso corporal.", "Progress photos": "Fotos de progreso", "Keep a visual record.": "Conserva un registro visual.", "Save photo": "Guardar foto",
    "Your weekly split.": "Tu división semanal.", "Start Workout": "Iniciar entrenamiento", "Start workout": "Iniciar entrenamiento", "Log a workout": "Registrar un entrenamiento", "Workout history": "Historial de entrenamientos", "No workouts saved yet.": "Aún no hay entrenamientos guardados.", "View session": "Ver sesión", "Workout complete": "Entrenamiento completado", "Session saved.": "Sesión guardada.", "Duration": "Duración", "Working sets": "Series de trabajo", "Tracked volume": "Volumen registrado", "Verified personal records": "Récords personales verificados", "Saved next-session targets": "Objetivos guardados para la próxima sesión", "View progress": "Ver progreso", "Ask SYLRIX about this workout": "Pregunta a SYLRIX sobre este entrenamiento",
    "Replace exercise": "Reemplazar ejercicio", "Add note": "Agregar nota", "Save note": "Guardar nota", "Finish workout": "Finalizar entrenamiento", "Rest timer": "Temporizador de descanso", "Complete": "Completar", "RPE": "RPE", "Last time": "Última vez", "Progression": "Progresión", "Check in before deciding how to train.": "Regístrate antes de decidir cómo entrenar.",
}


def localize_html(html, language="en"):
    """Translate legacy literal template copy without altering stored identifiers."""
    if normalize_language(language) != "es":
        return html
    for english, spanish in sorted(HTML_TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True):
        html = html.replace(english, spanish)
    return html


TRANSLATIONS["es"].update({
    "Menu": "Menú", "More": "Más", "Log workout": "Registrar entrenamiento", "Install SYLRIX.FIT": "Instalar SYLRIX.FIT",
    "Today": "Hoy", "Today’s workout": "Entrenamiento de hoy", "Continue workout": "Continuar entrenamiento", "Start workout": "Comenzar entrenamiento",
    "Log food": "Registrar comida", "Today’s readiness": "Preparación de hoy", "Edit check-in": "Editar registro", "Check in": "Registrarme",
    "Body weight": "Peso corporal", "Goal": "Objetivo", "Set a goal in Profile": "Define un objetivo en Perfil", "Update steps": "Actualizar pasos",
    "Recent progress": "Progreso reciente", "Review history": "Ver historial", "Open Coach": "Abrir Coach", "Ask with today’s data.": "Consulta con los datos de hoy.",
    "Join SYLRIX": "Únete a SYLRIX", "Email": "Correo electrónico", "Create account": "Crear cuenta", "Already a member?": "¿Ya eres miembro?",
    "Sign in": "Iniciar sesión", "Private-beta invite code": "Código de invitación beta privada", "At least 12 characters": "Al menos 12 caracteres",
    "Find the right movement.": "Encuentra el movimiento adecuado.", "Exercise library": "Biblioteca de ejercicios", "All muscles": "Todos los músculos", "All equipment": "Todo el equipo", "All levels": "Todos los niveles",
    "Primary muscle": "Músculo principal", "Difficulty": "Dificultad", "View exercise": "Ver ejercicio", "Movement details": "Detalles del movimiento", "Back to exercise library": "Volver a la biblioteca de ejercicios",
    "Muscle anatomy": "Anatomía muscular", "Front": "Frente", "Secondary": "Secundario", "How to perform": "Cómo realizarlo", "Execution notes": "Notas de ejecución",
    "Body-weight trend": "Tendencia de peso corporal", "Current weight": "Peso actual", "Starting weight": "Peso inicial", "Change logged": "Cambio registrado", "Goal weight": "Peso objetivo", "Log body weight": "Registrar peso corporal",
    "Weight entries": "Registros de peso", "Edit": "Editar", "Delete": "Eliminar", "Save weight": "Guardar peso", "Body weight (lb)": "Peso corporal (lb)",
    "Create a read-only guest link. It never exposes your profile, notes, history, nutrition, or progress data.": "Crea un enlace de invitado de solo lectura. Nunca muestra tu perfil, notas, historial, nutrición ni datos de progreso.",
    "QR code for shared workout": "Código QR del entrenamiento compartido", "Show QR Code": "Mostrar código QR", "Copied": "Copiado", "Rest": "Descanso",
    "Create your member profile first.": "Primero crea tu perfil de miembro.", "The public workout link was revoked.": "El enlace público del entrenamiento fue revocado.", "A private guest workout link is ready to share.": "El enlace privado para invitados está listo para compartir.",
    "Search by movement or muscle. Alternatives respect the signed-in athlete’s equipment, goals, and stated limitations.": "Busca por movimiento o músculo. Las alternativas respetan el equipo, los objetivos y las limitaciones indicadas.",
    "Bench Press, Pull-Up, Romanian Deadlift": "Press de banca, dominada, peso muerto rumano", "Search exercises": "Buscar ejercicios", "Filter by muscle": "Filtrar por músculo", "Filter by equipment": "Filtrar por equipo", "Filter by difficulty": "Filtrar por dificultad",
    "Exercise results": "Resultados de ejercicios", "No exercises found": "No se encontraron ejercicios", "Try a broader exercise name or choose another muscle group.": "Prueba un nombre más amplio o elige otro grupo muscular.",
    "Search by movement or muscle. Alternatives respect the signed-in athlete’s equipment, goals, and stated limitations.": "Busca por movimiento o músculo. Las alternativas respetan el equipo, los objetivos y las limitaciones indicadas.",
    "Category": "Categoría", "Level": "Nivel", "Detailed instructions are not available for this library entry.": "No hay instrucciones detalladas disponibles para este ejercicio.",
    "Today.": "Hoy.", "Good morning": "Buenos días", "Good afternoon": "Buenas tardes", "Good evening": "Buenas noches", "One view of your training, fuel, movement, and progress.": "Una vista de tu entrenamiento, nutrición, movimiento y progreso.",
    "Your completed sets are saved. Pick up where you left off.": "Tus series completadas están guardadas. Continúa donde lo dejaste.", "Train your next planned session.": "Entrena tu próxima sesión planificada.", "days per week": "días por semana", "calories": "calorías", "protein": "proteína", "calories remaining": "calorías restantes",
    "Your training history, progress photos, step quests, and plans stay private to your account.": "Tu historial de entrenamiento, fotos de progreso, pasos y planes permanecen privados en tu cuenta.",
    "Day": "Día", "Elapsed": "Transcurrido", "exercises": "ejercicios", "sets": "series", "Strength": "Fuerza", "Bodybuilding": "Musculación", "Powerlifting": "Powerlifting", "Powerbuilding": "Powerbuilding", "Calisthenics": "Calistenia", "Endurance": "Resistencia", "General Fitness": "Acondicionamiento general", "Crossfit": "CrossFit",
    "Bodyweight": "Peso corporal", "Full Gym": "Gimnasio completo", "Beginner": "Principiante", "Intermediate": "Intermedio", "Advanced": "Avanzado", "Easy": "Fácil", "Medium": "Medio", "Hard": "Difícil",
    "Practical guidance for your training.": "Orientación práctica para tu entrenamiento.", "Clear answers based on your plan, workouts, nutrition targets, and steps.": "Respuestas claras basadas en tu plan, entrenamientos, objetivos de nutrición y pasos.",
    "Free local Coach mode is on.": "El modo local gratuito de Coach está activo.", "No OpenAI requests or API credits are being used.": "No se usan solicitudes de OpenAI ni créditos de API.", "Your message": "Tu mensaje", "Ask a question…": "Haz una pregunta…", "Send": "Enviar", "Thinking…": "Pensando…",
})
