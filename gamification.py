RANKS = [
    ("F", 0, "Recruit"),
    ("E", 100, "Starter"),
    ("D", 250, "Rising"),
    ("C", 500, "Committed"),
    ("B", 900, "Challenger"),
    ("A", 1500, "Champion"),
    ("S", 2500, "Elite"),
]


def player_status(workout_logs, progress_photos, step_goals=0):
    """Award visible progress for completed actions, never for appearance."""
    xp = workout_logs * 25 + progress_photos * 15 + step_goals * 10
    rank, floor, title = RANKS[0]
    next_rank = None
    for candidate_rank, candidate_floor, candidate_title in RANKS:
        if xp >= candidate_floor:
            rank, floor, title = candidate_rank, candidate_floor, candidate_title
        elif next_rank is None:
            next_rank = (candidate_rank, candidate_floor, candidate_title)
    if next_rank:
        progress = round((xp - floor) / (next_rank[1] - floor) * 100)
        remaining = next_rank[1] - xp
    else:
        progress, remaining = 100, 0
    return {"xp": xp, "rank": rank, "title": title, "progress": max(0, min(progress, 100)), "next_rank": next_rank[0] if next_rank else None, "remaining": remaining, "workout_logs": workout_logs, "progress_photos": progress_photos}
