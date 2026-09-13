# SYLRIX Phase 1 architecture

## Repository review

The Flask application, SQLite member data, templates, nutrition helper, and daily workout feature are all usable and remain intact. `data/exercises.json` has 876 source exercises with primary/secondary muscles, equipment, difficulty, mechanic, and category.

The primary training-engine issues were: duplicate `generate_workout` and `generate_daily_workout_for_level` definitions in `workouts.py`; random selection causing non-repeatable plans; no typed profile/exercise model; and no distinct separation between source loading, filtering, and programming. The source file does not include movement pattern, rep ranges, goal tags, or substitutions, so Phase 1 derives movement patterns and prescriptions conservatively.

## New structure

```
training/
  models.py              typed Exercise, UserProfile, TrainingGoal
  exercise_repository.py bundled-data loading and normalization
  filtering.py           eligibility, ranking, substitutions
  programming.py         split choice, exercise order, prescriptions
tests/
  test_training_engine.py
```

The Flask adapter remains `workouts.py`. This keeps the engine independent of Flask and SQLite so it can later be exposed by FastAPI and backed by PostgreSQL.

## Incremental plan

1. Add typed models, deterministic filtering, split selection, and tests. **Complete.**
2. Route normal member plans through this engine while retaining special calisthenics/functional plans. **Next.**
3. Add structured exercise substitutions and program/history tables.
4. Move persistence behind repositories, then migrate SQLite to PostgreSQL when deployment needs it.

## Phase 1.5 customization

`TrainingPreferences` holds optional rep, set, equipment, exercise-count, and programming-mode controls without coupling the engine to the web form. `find_substitutes` returns available alternatives with a normalized suitability score and explanation. `editing.py` offers immutable replacement and prescription edits; callers validate results through `validate_workout` in `validation.py` before saving or displaying them.
