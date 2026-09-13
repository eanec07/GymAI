import json
import random


def load_exercises():
    with open("data/exercises.json", "r") as file:
        exercises = json.load(file)

    return exercises


def generate_workout(equipment, experience, days):

    exercises = load_exercises()

    equipment = equipment.lower().strip()
    experience = experience.lower().strip()

    # Handle common equipment names
    if equipment == "dumbbells":
        equipment = "dumbbell"

    if equipment == "kettlebell":
        equipment = "kettlebells"

    # Convert advanced to the database's "expert"
    if experience == "advanced":
        experience = "expert"

    # Find exercises matching equipment AND experience
    matching_exercises = []

    for exercise in exercises:

        exercise_equipment = (exercise["equipment"] or "").lower()
        exercise_level = (exercise["level"] or "").lower()

        if (
            equipment == exercise_equipment
            and experience == exercise_level
        ):
            matching_exercises.append(exercise)

    print(
        f"\nGym AI found {len(matching_exercises)} "
        f"exercises for your equipment and experience."
    )

    # Find chest exercises using both primary and secondary muscles
    chest_exercises = []

    for exercise in matching_exercises:

        primary_muscles = exercise["primaryMuscles"]
        secondary_muscles = exercise["secondaryMuscles"]

        if "chest" in primary_muscles or "chest" in secondary_muscles:
            chest_exercises.append(exercise)

    print(f"Gym AI found {len(chest_exercises)} chest exercises.")

    for exercise in chest_exercises[:10]:
        print(exercise["name"])

    # Randomly select 6 exercises
    selected_exercises = random.sample(
        matching_exercises,
        min(6, len(matching_exercises))
    )

    print("\nSelected exercises:")

    for exercise in selected_exercises:
        print(exercise["name"])

    return []