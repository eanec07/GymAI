document.addEventListener("DOMContentLoaded", () => {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach((node) => {
    node.nodeValue = node.nodeValue.replace(/\bquests?\b/gi, (word) => {
      const replacement = word.toLowerCase() === "quests" ? "challenges" : "challenge";
      return word[0] === word[0].toUpperCase() ? replacement[0].toUpperCase() + replacement.slice(1) : replacement;
    });
  });
  const categoryPaths = {Strength: "strength", Bodybuilding: "bodybuilding", Calisthenics: "calisthenics", Running: "endurance", Powerbuilding: "powerbuilding", "General fitness": "general-fitness"};
  document.querySelectorAll(".mode-card").forEach((card) => {
    const path = categoryPaths[card.querySelector("strong")?.textContent.trim()];
    if (!path) return;
    card.tabIndex = 0;
    card.setAttribute("role", "link");
    const open = () => { window.location.href = `/training/${path}`; };
    card.addEventListener("click", open);
    card.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); open(); } });
  });
});
