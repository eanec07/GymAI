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
    "Train · fuel · recover · evolve": "Entrena · aliméntate · recupérate · evoluciona", "Train with intent.": "Entrena con intención.", "More than fitness.": "Más que fitness.", "A stronger you.": "Una versión más fuerte de ti.", "A thoughtful home for personalized training, practical nutrition targets, and progress you can actually use.": "Un espacio para entrenamiento personalizado, objetivos prácticos de nutrición y progreso que realmente puedes usar.", "Choose a training path": "Elige una ruta de entrenamiento", "Workouts": "Entrenamientos", "Plans for your goals": "Planes para tus objetivos", "Tracking": "Seguimiento", "Log real progress": "Registra progreso real", "Recovery": "Recuperación", "Mobility and guidance": "Movilidad y orientación", "Built for every journey": "Creado para cada camino", "Training that adapts to you.": "Entrenamiento que se adapta a ti.", "Choose a path, answer a few focused questions, and build a plan around your equipment, time, and experience.": "Elige una ruta, responde algunas preguntas y crea un plan según tu equipo, tiempo y experiencia.", "Build raw power.": "Desarrolla fuerza real.", "Build muscle and size.": "Desarrolla músculo y tamaño.", "Train anywhere.": "Entrena en cualquier lugar.", "Go farther, steadily.": "Llega más lejos, paso a paso.", "Move better every day.": "Muévete mejor cada día.", "Strength and size.": "Fuerza y tamaño.", "Squat. Bench. Deadlift.": "Sentadilla. Press de banca. Peso muerto.", "Train work capacity.": "Entrena tu capacidad de trabajo.", "Fuel with clarity.": "Aliméntate con claridad.", "Keep the proof.": "Conserva la evidencia.", "Guidance with context.": "Orientación con contexto.", "Real tools. Real progress.": "Herramientas reales. Progreso real.", "Tell us about you": "Cuéntanos sobre ti", "Pick a path": "Elige una ruta", "Get your program": "Obtén tu programa", "Train and log": "Entrena y registra", "Start with the next workout.": "Comienza con el próximo entrenamiento.",
    "View day": "Ver día", "Fuel the work you actually do.": "Alimenta el trabajo que realmente haces.", "Targets come from your saved profile. Log foods yourself; SYLRIX keeps the daily totals clear.": "Los objetivos provienen de tu perfil guardado. Registra tus alimentos; SYLRIX mantiene claros los totales diarios.", "over target": "por encima del objetivo", "remaining": "restante", "Serving / description": "Porción / descripción", "Save food": "Guardar alimento", "Recent foods": "Alimentos recientes", "Log again": "Registrar de nuevo", "Foods logged": "Alimentos registrados", "No foods logged for this day.": "No hay alimentos registrados para este día.", "Recent days:": "Días recientes:",
    "Training path": "Ruta de entrenamiento", "Build your": "Crea tu", "program.": "programa.", "What you can work toward": "En qué puedes trabajar", "Your guided setup": "Tu configuración guiada", "Questions that matter": "Preguntas importantes", "Recommended starting split": "División inicial recomendada", "Use this training style": "Usar este estilo de entrenamiento", "Gym floor calendar": "Calendario de entrenamiento", "Train with the week.": "Entrena con la semana.", "Choose your experience level": "Elige tu nivel de experiencia", "Update session": "Actualizar sesión", "Want your own program?": "¿Quieres tu propio programa?", "Choose your training style.": "Elige tu estilo de entrenamiento.", "Build my plan": "Crear mi plan",
    "Daily movement quest": "Objetivo diario de movimiento", "Every step moves the story forward.": "Cada paso hace avanzar tu historia.", "steps today": "pasos hoy", "Daily goal": "Objetivo diario", "Save step count": "Guardar pasos", "Last seven days": "Últimos siete días", "Movement history": "Historial de movimiento", "Quest": "Objetivo", "In progress": "En progreso", "Complete +10 XP": "Completado +10 XP",
    "INSPIRATION, MADE PERSONAL": "INSPIRACIÓN, HECHA PERSONAL", "Build your physique path": "Crea tu ruta física", "Inspiration": "Inspiración", "What matters most?": "¿Qué importa más?", "Create my path": "Crear mi ruta", "Starting weight": "Peso inicial", "Suggested pace": "Ritmo sugerido", "Training emphasis:": "Enfoque de entrenamiento:", "Next step:": "Siguiente paso:",
    "TRANSPARENT DATA POLICY": "POLÍTICA DE DATOS TRANSPARENTE", "Where SYLRIX information comes from": "De dónde proviene la información de SYLRIX", "Refresh:": "Actualización:", "Status:": "Estado:", "Creator content": "Contenido de creadores", "That action was not accepted.": "Esa acción no fue aceptada.", "This page is not here.": "Esta página no existe.", "Please slow down.": "Reduce la velocidad.", "Something went wrong.": "Algo salió mal.", "Try again, return to your dashboard, or sign in if your session has ended.": "Inténtalo de nuevo, vuelve a tu panel o inicia sesión si tu sesión terminó.", "Go home": "Ir al inicio", "Private beta": "Beta privada",
    "Step 1 / Build your profile": "Paso 1 / Crea tu perfil", "Your goals don’t need to fit in a box.": "Tus objetivos no tienen que caber en una sola categoría.", "Start with the basics. Your selected training path adds only the questions that matter for that path.": "Comienza con lo básico. Tu ruta de entrenamiento añade solo las preguntas relevantes.",
    "Core profile": "Perfil básico", "Name": "Nombre", "Age": "Edad", "Sex": "Sexo", "Male": "Hombre", "Female": "Mujer", "Height (in)": "Estatura (pulg)", "Training basics": "Bases del entrenamiento", "Main goal": "Objetivo principal", "Build muscle": "Ganar músculo", "Lose fat": "Perder grasa", "Build strength": "Ganar fuerza", "Maintain or recomposition": "Mantener o recomponer", "Build endurance": "Mejorar resistencia", "Training days/week": "Días de entrenamiento/semana", "Training path": "Ruta de entrenamiento", "Choose later": "Elegir después", "Equipment access": "Acceso a equipo", "Dumbbells": "Mancuernas", "Barbell and rack": "Barra y rack", "Bodyweight only": "Solo peso corporal", "Other / mixed equipment": "Otro / equipo mixto", "Time per workout": "Tiempo por entrenamiento", "About 30 minutes": "Aproximadamente 30 minutos", "About 45 minutes": "Aproximadamente 45 minutos", "About 60 minutes": "Aproximadamente 60 minutos", "75+ minutes": "Más de 75 minutos", "What do you want to achieve?": "¿Qué quieres lograr?", "Other equipment you have": "Otro equipo que tienes", "Optional preferences": "Preferencias opcionales", "Favorite exercises": "Ejercicios favoritos", "Exercises to avoid": "Ejercicios que deseas evitar", "Injuries or limitations": "Lesiones o limitaciones", "Create my plan": "Crear mi plan",
    "Edit profile": "Editar perfil", "Display name": "Nombre visible", "Current weight (lb)": "Peso actual (lb)", "Goal weight (lb)": "Peso objetivo (lb)", "Primary goal": "Objetivo principal", "Training style": "Estilo de entrenamiento", "Experience": "Experiencia", "Days per week": "Días por semana", "Session length (minutes)": "Duración de sesión (minutos)", "Available equipment": "Equipo disponible", "Save profile": "Guardar perfil", "Reset setup": "Reiniciar configuración",
    "Daily check-in": "Registro diario", "How are you feeling today?": "¿Cómo te sientes hoy?", "Sleep hours": "Horas de sueño", "Sleep quality": "Calidad del sueño", "Energy": "Energía", "Soreness": "Dolor muscular", "Stress": "Estrés", "Motivation": "Motivación", "Anything relevant?": "¿Algo relevante?", "Update check-in": "Actualizar registro", "Save check-in": "Guardar registro", "Today’s readiness": "Preparación de hoy", "Your result": "Tu resultado", "Ready when you are.": "Listo cuando tú lo estés.", "Last seven days": "Últimos siete días",
    "Daily nutrition": "Nutrición diaria", "Calories": "Calorías", "Carbs": "Carbohidratos", "Fat": "Grasas", "Fiber": "Fibra", "Add food": "Agregar comida", "Food": "Alimento", "Serving": "Porción", "Recent foods": "Alimentos recientes", "No food entries yet.": "Aún no hay registros de alimentos.", "Edit food": "Editar alimento", "Delete food": "Eliminar alimento", "Food entry saved.": "Registro de alimento guardado.",
    "Track the work, not guesses.": "Registra el trabajo, no las suposiciones.", "Body-weight trend": "Tendencia de peso corporal", "Log body weight": "Registrar peso corporal", "Date": "Fecha", "Weight entries": "Registros de peso", "No body-weight entries yet.": "Aún no hay registros de peso corporal.", "Progress photos": "Fotos de progreso", "Keep a visual record.": "Conserva un registro visual.", "Save photo": "Guardar foto",
    "Your weekly split.": "Tu división semanal.", "Start Workout": "Iniciar entrenamiento", "Start workout": "Iniciar entrenamiento", "Log a workout": "Registrar un entrenamiento", "Workout history": "Historial de entrenamientos", "No workouts saved yet.": "Aún no hay entrenamientos guardados.", "View session": "Ver sesión", "Workout complete": "Entrenamiento completado", "Session saved.": "Sesión guardada.", "Duration": "Duración", "Working sets": "Series de trabajo", "Tracked volume": "Volumen registrado", "Verified personal records": "Récords personales verificados", "Saved next-session targets": "Objetivos guardados para la próxima sesión", "View progress": "Ver progreso", "Ask SYLRIX about this workout": "Pregunta a SYLRIX sobre este entrenamiento",
    "Replace exercise": "Reemplazar ejercicio", "Add note": "Agregar nota", "Save note": "Guardar nota", "Finish workout": "Finalizar entrenamiento", "Rest timer": "Temporizador de descanso", "Complete": "Completar", "RPE": "RPE", "Last time": "Última vez", "Progression": "Progresión", "Check in before deciding how to train.": "Regístrate antes de decidir cómo entrenar.",
}

# Literal presentation copy in legacy templates is translated after rendering so
# stored workout values, share tokens, identifiers, and source exercise data are
# never changed. Keep longer phrases here to avoid partial replacements.
HTML_TRANSLATIONS.update({
    "SYLRIX.FIT / Member profile": "SYLRIX.FIT / Perfil de miembro",
    "Keep the inputs that shape your training current. Account credentials and other members’ data are never shown here.": "Mantén actualizados los datos que dan forma a tu entrenamiento. Las credenciales de la cuenta y los datos de otros miembros nunca se muestran aquí.",
    "Account": "Cuenta", "Training": "Entrenamiento", "Style not selected": "Estilo no seleccionado",
    "No goal weight set": "No hay peso objetivo definido", "Favorite exercises": "Ejercicios favoritos",
    "Exercises to avoid": "Ejercicios que deseas evitar", "Build a new fitness setup.": "Crea una nueva configuración de fitness.",
    "This clears your profile and plan inputs, but keeps your account and past logs.": "Esto borra los datos de tu perfil y plan, pero conserva tu cuenta y registros anteriores.",
    "Type RESET to confirm": "Escribe RESET para confirmar", "Restart setup": "Reiniciar configuración",
    "SYLRIX stores the account, training, nutrition, progress, and photo information you choose to enter so it can provide member-specific features. Private beta data handling must be formally reviewed before any public or commercial launch.": "SYLRIX almacena la información de cuenta, entrenamiento, nutrición, progreso y fotos que decides ingresar para ofrecer funciones personalizadas. El manejo de datos de la beta privada debe revisarse formalmente antes de cualquier lanzamiento público o comercial.",
    "SYLRIX provides general fitness organization and educational guidance, not medical advice. This private-beta placeholder requires formal legal review before public or commercial use.": "SYLRIX ofrece organización general de fitness y orientación educativa, no asesoramiento médico. Este texto provisional de beta privada requiere revisión legal formal antes del uso público o comercial.",
    "Privacy": "Privacidad", "Terms": "Términos",
    "Strength": "Fuerza", "Bodybuilding": "Musculación", "General fitness": "Acondicionamiento general",
    "CrossFit-style training": "Entrenamiento estilo CrossFit", "Calisthenics": "Calistenia", "Endurance": "Resistencia",
    "Build foundational lifts · Progress with confidence": "Desarrolla levantamientos fundamentales · Progresa con confianza",
    "Prioritize muscle groups · Build balanced size · Bring up weak points": "Prioriza grupos musculares · Desarrolla tamaño equilibrado · Mejora puntos débiles",
    "Build squat · Build bench press · Build deadlift": "Mejora sentadilla · Mejora press de banca · Mejora peso muerto",
    "Build big lifts · Add productive hypertrophy volume": "Mejora levantamientos grandes · Añade volumen productivo de hipertrofia",
    "Improve engine · Build functional strength · Train mixed-modal fitness": "Mejora tu motor · Desarrolla fuerza funcional · Entrena fitness multimodal",
    "Stronger basics · Better pull-ups and dips · Skill progress": "Bases más fuertes · Mejores dominadas y fondos · Progreso técnico",
    "Move better · Feel stronger · Build a sustainable habit": "Muévete mejor · Siéntete más fuerte · Crea un hábito sostenible",
    "Build weekly capacity · Prepare for a distance · Improve consistency": "Desarrolla capacidad semanal · Prepárate para una distancia · Mejora la consistencia",
    "Built around the work you actually log.": "Creado alrededor del trabajo que realmente registras.",
    "Targets, with more coming": "Objetivos, y más próximamente", "Exercise library": "Biblioteca de ejercicios",
    "Find the right movement": "Encuentra el movimiento adecuado", "Nutrition · planned next": "Nutrición · próximamente",
    "Today, members can view calorie and protein targets. Food logging, barcode scanning, recipes, and meal planning are planned—not represented as finished features.": "Hoy, los miembros pueden ver objetivos de calorías y proteína. El registro de alimentos, escaneo de códigos, recetas y planificación de comidas están previstos, no se presentan como funciones terminadas.",
    "View current targets →": "Ver objetivos actuales →", "Progress tracking": "Seguimiento de progreso",
    "Log lifts, steps, notes, and private progress photos. Build a history that makes the next decision easier.": "Registra levantamientos, pasos, notas y fotos privadas de progreso. Crea un historial que facilite la próxima decisión.",
    "Start tracking →": "Comenzar el seguimiento →", "Make room to recover.": "Haz espacio para recuperarte.",
    "Mobility and exercise modifications should support training—not replace qualified medical care or diagnosis.": "La movilidad y las modificaciones de ejercicios deben apoyar el entrenamiento, no reemplazar la atención médica o el diagnóstico profesional.",
    "View daily training →": "Ver entrenamiento diario →", "Coach conversations use your saved training data when the service is configured.": "Las conversaciones con Coach usan tus datos de entrenamiento guardados cuando el servicio está configurado.",
    "Open Coach →": "Abrir Coach →", "How SYLRIX works": "Cómo funciona SYLRIX",
    "Goals, experience, equipment, time, and preferences.": "Objetivos, experiencia, equipo, tiempo y preferencias.",
    "Strength, physique, endurance, calisthenics, or functional training.": "Fuerza, físico, resistencia, calistenia o entrenamiento funcional.",
    "Structured around the tools and movements available to you.": "Estructurado según las herramientas y movimientos que tienes disponibles.",
    "Keep lifts, notes, steps, and progress in one place.": "Mantén levantamientos, notas, pasos y progreso en un solo lugar.",
    "Reborn. Reforged. Relentless.": "Renacido. Reforjado. Implacable.",
    "SYLRIX is growing carefully around practical training tools—not empty promises.": "SYLRIX crece cuidadosamente alrededor de herramientas prácticas de entrenamiento, no promesas vacías.",
    "Build muscle through balanced hypertrophy training, practical volume, and progressive overload.": "Desarrolla músculo con entrenamiento equilibrado de hipertrofia, volumen práctico y sobrecarga progresiva.",
    "Build your squat, bench press, and deadlift with focused strength progression.": "Mejora tu sentadilla, press de banca y peso muerto con progresión de fuerza enfocada.",
    "Combine big-lift strength with enough volume to build a capable physique.": "Combina fuerza en levantamientos grandes con suficiente volumen para desarrollar un físico capaz.",
    "Develop conditioning and full-body capacity with scalable functional sessions.": "Desarrolla acondicionamiento y capacidad de cuerpo completo con sesiones funcionales escalables.",
    "Use bodyweight strength, pull-up progressions, and minimal equipment.": "Usa fuerza con peso corporal, progresiones de dominadas y equipo mínimo.",
    "Train foundational movements with clear progression and useful rep ranges.": "Entrena movimientos fundamentales con progresión clara y rangos de repeticiones útiles.",
    "Build a sustainable routine for strength, movement, and everyday energy.": "Crea una rutina sostenible para fuerza, movimiento y energía diaria.",
    "Build steady capacity and athletic consistency for longer efforts.": "Desarrolla capacidad constante y consistencia atlética para esfuerzos más largos.",
    "Use the setup to tell SYLRIX where you are today, then create a plan that fits your equipment and schedule.": "Usa la configuración para decirle a SYLRIX dónde estás hoy y crear un plan que se ajuste a tu equipo y horario.",
    "You can accept this, choose another compatible split, or let SYLRIX decide from your schedule.": "Puedes aceptar esto, elegir otra división compatible o dejar que SYLRIX decida según tu horario.",
    "Priority muscle groups, preferred split, volume comfort, and rep-range preference.": "Grupos musculares prioritarios, división preferida, tolerancia al volumen y rango de repeticiones preferido.",
    "Current or estimated maxes, competition interest, weak points, and preferred lift frequency.": "Máximos actuales o estimados, interés en competir, puntos débiles y frecuencia de levantamientos preferida.",
    "Strength targets, muscle priorities, current squat / bench / deadlift numbers, and frequency.": "Objetivos de fuerza, prioridades musculares, marcas actuales de sentadilla / banca / peso muerto y frecuencia.",
    "Conditioning level, barbell access, rower or bike access, kettlebells, pull-up rig, and session duration.": "Nivel de acondicionamiento, acceso a barra, remo o bicicleta, pesas rusas, barra de dominadas y duración de sesión.",
    "Current pull-up, push-up, and dip ability; pull-up bar, rings, dip bars, bands, and skill goals.": "Capacidad actual de dominadas, flexiones y fondos; barra de dominadas, anillas, barras de fondos, bandas y objetivos técnicos.",
    "Primary lifts, available rack and barbell, strength target, and preferred frequency.": "Levantamientos principales, rack y barra disponibles, objetivo de fuerza y frecuencia preferida.",
    "Main health goal, days available, session duration, and realistic equipment access.": "Objetivo principal de salud, días disponibles, duración de sesión y acceso realista a equipo.",
    "Weekly mileage, current running frequency, preferred distance, pace if known, and limitations.": "Kilometraje semanal, frecuencia actual de carrera, distancia preferida, ritmo si se conoce y limitaciones.",
    "Upper / Lower or Push / Pull / Legs": "Superior / Inferior o Empuje / Tirón / Piernas",
    "3- or 4-day squat / bench / deadlift layout": "Distribución de sentadilla / banca / peso muerto de 3 o 4 días",
    "Upper / Lower strength + hypertrophy": "Superior / Inferior de fuerza + hipertrofia",
    "Alternating engine and strength + conditioning days": "Días alternos de motor y fuerza + acondicionamiento",
    "Push / Pull / Legs or Upper / Lower + skill work": "Empuje / Tirón / Piernas o Superior / Inferior + trabajo técnico",
    "Upper / Lower or full-body strength": "Superior / Inferior o fuerza de cuerpo completo",
    "Balanced full-body plan": "Plan equilibrado de cuerpo completo",
    "Running frequency plan + simple strength support": "Plan de frecuencia de carrera + apoyo simple de fuerza",
    "Training and nutrition claims should show their source and review status. SYLRIX should never silently scrape creator content or turn social posts into medical guidance.": "Las afirmaciones de entrenamiento y nutrición deben mostrar su fuente y estado de revisión. SYLRIX nunca debe extraer silenciosamente contenido de creadores ni convertir publicaciones sociales en orientación médica.",
    "Jeff Nippard, Chris Bumstead, and other creators can be added as labeled inspiration or staff-curated education links only after permission and source review. Their content is not a substitute for individualized clinical, nutrition, or coaching advice.": "Jeff Nippard, Chris Bumstead y otros creadores pueden añadirse como inspiración etiquetada o enlaces educativos seleccionados por el equipo solo después de permiso y revisión de fuentes. Su contenido no sustituye el asesoramiento clínico, nutricional o de entrenamiento individualizado.",
    "Enter today’s count from your phone, watch, or fitness tracker. Complete your step goal to earn 10 XP.": "Ingresa el conteo de hoy desde tu teléfono, reloj o monitor de actividad. Completa tu objetivo de pasos para ganar 10 XP.",
    "Quest complete—your 10 XP is earned!": "¡Objetivo completado: ganaste 10 XP!", "more steps to complete today’s quest.": "pasos más para completar el objetivo de hoy.",
    "Today’s steps": "Pasos de hoy", "Daily step goal": "Objetivo diario de pasos", "The future integration": "La futura integración", "Phone sync is coming with the native app.": "La sincronización con el teléfono llegará con la aplicación nativa.",
    "When SYLRIX is packaged as a phone app, members will be able to choose HealthKit on iPhone or Health Connect on Android and grant permission for their steps to sync automatically. Until then, this tracker keeps the habit and the quest system working.": "Cuando SYLRIX se empaquete como aplicación de teléfono, los miembros podrán elegir HealthKit en iPhone o Health Connect en Android y otorgar permiso para sincronizar sus pasos automáticamente. Hasta entonces, este registro mantiene el hábito y el sistema de objetivos funcionando.",
    "Body weight (lb)": "Peso corporal (lb)", "Body-weight line graph": "Gráfica de línea de peso corporal",
    "READINESS": "PREPARACIÓN", "High": "Alta", "Normal": "Normal", "Reduced": "Reducida", "Recovery": "Recuperación",
    "A quick readiness check-in will tailor today’s guidance.": "Un registro rápido de preparación adaptará la orientación de hoy.",
    "You are ready for your planned session. Keep the usual effort and stop if form changes.": "Estás listo para tu sesión planificada. Mantén el esfuerzo habitual y detente si cambia tu técnica.",
    "Train as planned, but keep one or two reps in reserve on harder sets.": "Entrena según lo planeado, pero deja una o dos repeticiones en reserva en las series más exigentes.",
    "Keep the session, but reduce load or volume if it feels harder than usual.": "Mantén la sesión, pero reduce la carga o el volumen si se siente más difícil de lo habitual.",
    "Prioritize recovery today. Choose easy movement, mobility, or a rest day.": "Prioriza la recuperación hoy. Elige movimiento fácil, movilidad o un día de descanso.",
    "Log / view progress": "Registrar / ver progreso", "Keep movement consistent today.": "Mantén el movimiento constante hoy.",
    "Build your record": "Crea tu historial", "Complete a workout to establish progress.": "Completa un entrenamiento para establecer progreso.",
    "Weight PR": "Récord de peso", "Estimated 1RM": "1RM estimado", "Increase": "Aumentar", "Hold": "Mantener", "Deload": "Descargar",
    "Ask with today’s data.": "Consulta con los datos de hoy.", "Try: “How ready am I today?” · “How much protein do I have left?” · “How is my progress?”": "Prueba: “¿Qué tan preparado estoy hoy?” · “¿Cuánta proteína me queda?” · “¿Cómo va mi progreso?”",
    "Add at least two entries to view a trend.": "Agrega al menos dos registros para ver una tendencia.", "Set a goal weight in Profile": "Define un peso objetivo en Perfil",
    "Resume": "Reanudar", "Note:": "Nota:", "Exercise note": "Nota del ejercicio", "Technique, setup, or next-session reminder": "Técnica, preparación o recordatorio para la próxima sesión",
})


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
    "Body weight (lb)": "Peso corporal (lb)", "Body-weight line graph": "Gráfica de línea de peso corporal",
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
    "READINESS": "PREPARACIÓN", "High": "Alta", "Normal": "Normal", "Reduced": "Reducida", "Recovery": "Recuperación",
    "Train as planned. Your check-in supports a strong training day.": "Entrena según lo planeado. Tu registro respalda un buen día de entrenamiento.",
    "Train as planned and use your saved progression targets if they feel technically solid.": "Entrena según lo planeado y usa tus objetivos de progresión guardados si se sienten técnicamente sólidos.",
    "Train as planned, keeping form and effort controlled.": "Entrena según lo planeado, manteniendo técnica y esfuerzo controlados.",
    "Reduce volume by one working set per exercise today.": "Reduce hoy el volumen en una serie de trabajo por ejercicio.",
    "Train today, but reduce working weights by approximately 5%.": "Entrena hoy, pero reduce los pesos de trabajo aproximadamente un 5%.",
    "A rest day is the conservative choice based on today’s check-in.": "Un día de descanso es la elección prudente según el registro de hoy.",
    "Choose an easy recovery-focused session, or rest if that feels better.": "Elige una sesión fácil enfocada en recuperación o descansa si te sientes mejor así.",
    "Log / view progress": "Registrar / ver progreso", "Keep movement consistent today.": "Mantén el movimiento constante hoy.",
    "Build your record": "Crea tu historial", "Complete a workout to establish progress.": "Completa un entrenamiento para establecer progreso.",
    "Weight PR": "Récord de peso", "Estimated 1RM": "1RM estimado", "Increase": "Aumentar", "Hold": "Mantener", "Deload": "Descargar",
    "Free local Coach mode is on.": "El modo local gratuito de Coach está activo.", "No OpenAI requests or API credits are being used.": "No se usan solicitudes de OpenAI ni créditos de API.", "Your message": "Tu mensaje", "Ask a question…": "Haz una pregunta…", "Send": "Enviar", "Thinking…": "Pensando…",
    "You": "Tú", "Local intelligence active": "Inteligencia local activa", "AI Coach online": "Coach de IA en línea", "Start here": "Comienza aquí", "What can I help with?": "¿En qué puedo ayudarte?", "Ask about a lift, your weight trend, recent training, nutrition targets, steps, recovery, or substitutions.": "Pregunta sobre un levantamiento, tu tendencia de peso, entrenamientos recientes, objetivos de nutrición, pasos, recuperación o sustituciones.",
    "Optional": "Opcional", "Example: slept poorly, legs feel heavy.": "Ejemplo: dormí mal, las piernas se sienten pesadas.", "readiness": "preparación", "Your score and session guidance appear here after this quick check-in.": "Tu puntuación y orientación de sesión aparecerán aquí después de este breve registro.", "Your recent readiness check-ins will appear here.": "Tus registros recientes de preparación aparecerán aquí.", "Use this as general training guidance—not medical clearance. Update it any time today.": "Úsalo como orientación general de entrenamiento, no como autorización médica. Puedes actualizarlo en cualquier momento hoy.", "Primary": "Principal", "Back": "Espalda", "Front muscular anatomy": "Anatomía muscular frontal", "Back muscular anatomy": "Anatomía muscular posterior", "Front muscular anatomy diagram": "Diagrama de anatomía muscular frontal", "Back muscular anatomy diagram": "Diagrama de anatomía muscular posterior",
    "Preferred workout split": "División de entrenamiento preferida", "SYLRIX Recommended": "Recomendado por SYLRIX", "Full Body": "Cuerpo completo", "Upper / Lower": "Superior / Inferior", "Push / Pull / Legs": "Empuje / Tirón / Piernas", "Your selection affects future generated workouts, not active or completed sessions.": "Tu selección afecta los entrenamientos generados en el futuro, no las sesiones activas o completadas.",
})
