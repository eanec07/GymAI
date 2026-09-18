/* Dependency-free, line-only SVG renderer for private body-weight history. */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".weight-chart").forEach((element) => {
    const points = JSON.parse(element.dataset.points || "[]");
    if (points.length < 2) return;
    const chartTitle = element.dataset.chartTitle || "Body weight (lb)";
    const goalLabel = element.dataset.goalLabel || "Goal";
    const chartAriaLabel = element.dataset.chartAriaLabel || "Body-weight line graph";

    const width = 700, height = 260;
    const padding = { top: 22, right: 24, bottom: 48, left: 54 };
    const goal = Number(element.dataset.goalWeight);
    const values = points.map(point => Number(point.weight));
    if (Number.isFinite(goal)) values.push(goal);
    const rawMin = Math.min(...values), rawMax = Math.max(...values);
    const spread = Math.max(rawMax - rawMin, 2);
    const min = Math.floor((rawMin - spread * .15) * 2) / 2;
    const max = Math.ceil((rawMax + spread * .15) * 2) / 2;
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const x = index => padding.left + index * (plotWidth / (points.length - 1));
    const y = value => padding.top + (max - value) * plotHeight / (max - min || 1);
    const coords = points.map((point, index) => `${x(index).toFixed(1)},${y(Number(point.weight)).toFixed(1)}`);
    const ticks = Array.from({ length: 4 }, (_, index) => min + (max - min) * index / 3);
    const grid = ticks.map(tick => `<g><line x1="${padding.left}" y1="${y(tick)}" x2="${width-padding.right}" y2="${y(tick)}" class="chart-grid"/><text x="${padding.left-9}" y="${y(tick)+4}" text-anchor="end" class="chart-y-label">${tick.toFixed(1)}</text></g>`).join("");
    const goalLine = Number.isFinite(goal) ? `<g class="chart-goal"><line x1="${padding.left}" y1="${y(goal)}" x2="${width-padding.right}" y2="${y(goal)}"/><text x="${width-padding.right}" y="${y(goal)-7}" text-anchor="end">${goalLabel} ${goal.toFixed(1)} lb</text></g>` : "";
    const dots = coords.map((point, index) => `<circle cx="${point.split(",")[0]}" cy="${point.split(",")[1]}" r="4" class="chart-dot"><title>${points[index].date}: ${Number(points[index].weight).toFixed(1)} lb</title></circle>`).join("");
    element.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${chartAriaLabel}: ${points[0].date} – ${points[points.length - 1].date}"><text x="${padding.left}" y="13" class="chart-title">${chartTitle}</text>${grid}${goalLine}<line x1="${padding.left}" y1="${height-padding.bottom}" x2="${width-padding.right}" y2="${height-padding.bottom}" class="chart-axis"/><polyline points="${coords.join(" ")}" class="chart-line"/>${dots}<text x="${padding.left}" y="${height-17}" class="chart-x-label">${points[0].date}</text><text x="${width-padding.right}" y="${height-17}" text-anchor="end" class="chart-x-label">${points[points.length - 1].date}</text></svg>`;
  });
});
