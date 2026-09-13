from nutrition import calculate_nutrition
from workouts import generate_workout

print("=== GYM AI ===")

name = input("What's your name? ")

age = int(input("How old are you? "))

sex = input("Sex (male/female): ").lower()

weight = float(input("Weight in pounds: "))
height = float(input("Height in inches: "))

goal = input("Goal (lose/gain/maintain): ").lower()

days = int(input("How many days per week do you train? "))
equipment = input("What equipment do you have? ")
print("\nHow would you describe your training experience?")
print("1. Beginner")
print("2. Intermediate")
print("3. Advanced")

experience_choice = input("Choose 1, 2, or 3: ")

if experience_choice == "1":
    experience = "beginner"
elif experience_choice == "2":
    experience = "intermediate"
elif experience_choice == "3":
    experience = "advanced"
else:
    experience = "beginner"
# Convert pounds/inches to metric
nutrition = calculate_nutrition(
    age,
    sex,
    weight,
    height,
    goal,
    days
)

print("\n=== YOUR GYM AI PLAN ===")

print(f"Name: {name}")
print(f"Goal: {nutrition['goal_type']}")
print(f"Training days: {days}")

print(f"\nEstimated maintenance calories: {nutrition['tdee']}")
print(f"Daily calorie target: {nutrition['calories']}")
print(f"Protein target: {nutrition['protein']} grams")

print("\n=== YOUR WORKOUT PLAN ===")

workouts = generate_workout(
    equipment,
    experience,
    days
)

for day_number, workout in enumerate(workouts, start=1):
    print(f"\nDAY {day_number} — {workout['name']}")

    for exercise in workout["exercises"]:
        print(exercise)