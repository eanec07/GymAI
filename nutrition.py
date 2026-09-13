def calculate_nutrition(age, sex, weight, height, goal, days):
    # Convert to metric
    weight_kg = weight * 0.453592
    height_cm = height * 2.54

    # Calculate BMR
    if sex == "male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    # Estimate activity
    if days <= 1:
        activity = 1.2
    elif days <= 3:
        activity = 1.375
    elif days <= 5:
        activity = 1.55
    else:
        activity = 1.725

    tdee = bmr * activity

    # Adjust calories based on goal
    if "lose" in goal or "fat" in goal or "cut" in goal:
        calories = tdee - 400
        goal_type = "Fat loss"

    elif "gain" in goal or "muscle" in goal or "bulk" in goal:
        calories = tdee + 250
        goal_type = "Muscle gain"

    else:
        calories = tdee
        goal_type = "Maintenance"

    # Protein target
    protein = weight * 0.8

    return {
        "goal_type": goal_type,
        "bmr": round(bmr),
        "tdee": round(tdee),
        "calories": round(calories),
        "protein": round(protein)
    }