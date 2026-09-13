def build_physique_path(member, inspiration, priority):
    """Provide a realistic, individualized process—not a promise to copy a physique."""
    goal = member["goal"].lower()
    bodyweight = member["weight"]
    if "fat" in goal or "lose" in goal:
        weekly_rate = "0.5–1.0% of bodyweight per week"
        next_step = "Use a modest calorie deficit, retain strength work, and reassess every 2–4 weeks."
    elif "gain" in goal or "muscle" in goal:
        weekly_rate = "0.25–0.5% of bodyweight per week"
        next_step = "Use a small calorie surplus, train each muscle group consistently, and reassess every 2–4 weeks."
    else:
        weekly_rate = "hold bodyweight within roughly 0.25% per week"
        next_step = "Use performance and measurements—not scale weight alone—to guide adjustments."
    emphasis = {
        "overall": "balanced full-body development and steady progressive overload",
        "upper": "upper-body volume: chest, back, shoulders, and arms",
        "lower": "lower-body strength: quads, glutes, hamstrings, and calves",
        "strength": "compound-lift technique, progressive loading, and recovery",
        "lean": "sustainable fat loss while preserving muscle and training performance",
    }.get(priority, "balanced full-body development and steady progressive overload")
    return {
        "inspiration": inspiration.strip() or "your chosen inspiration",
        "weekly_rate": weekly_rate,
        "current_weight": bodyweight,
        "emphasis": emphasis,
        "next_step": next_step,
        "disclaimer": "People differ in genetics, height, training history, body-fat distribution, access to enhancement drugs, and lifestyle. An inspiration is useful for setting a direction, not for predicting your final physique or exact lifting numbers.",
    }
