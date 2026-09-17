# Exercise anatomy asset strategy

The front and back anatomy diagram in `templates/components/muscle_diagram.html` is original, project-owned inline SVG geometry. It is not copied from a third-party anatomy illustration and has no external runtime dependency.

The SVG is rendered only on Exercise Detail pages. It uses `muscles.py` as its source of truth: canonical library labels are normalized, mapped to named SVG regions, and styled as primary (SYLRIX red), secondary (muted red), or neutral gray. Exercise Library result cards intentionally do not render anatomy SVGs, keeping search results lightweight.
