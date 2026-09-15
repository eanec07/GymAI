/* Small dependency-free SVG renderer for private body-weight history. */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".weight-chart").forEach((element) => {
    const points = JSON.parse(element.dataset.points || "[]");
    if (points.length < 2) return;
    const width = 700, height = 220, pad = 28;
    const values = points.map(point => Number(point.weight));
    const min = Math.min(...values), max = Math.max(...values), range = max - min || 1;
    const coords = values.map((value, index) => `${pad + index * ((width - pad * 2) / (values.length - 1))},${height - pad - ((value - min) / range) * (height - pad * 2)}`);
    element.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Body-weight chart"><line x1="${pad}" y1="${height-pad}" x2="${width-pad}" y2="${height-pad}" class="chart-axis"/><polyline points="${coords.join(" ")}" class="chart-line"/>${coords.map(point => `<circle cx="${point.split(',')[0]}" cy="${point.split(',')[1]}" r="4" class="chart-dot"/>`).join("")}</svg><div class="chart-labels"><span>${points[0].date}</span><strong>${min.toFixed(1)}–${max.toFixed(1)} lb</strong><span>${points.at(-1).date}</span></div>`;
  });
});
