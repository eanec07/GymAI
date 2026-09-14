document.addEventListener("DOMContentLoaded", () => {
  const brandStyles = document.createElement("link");
  brandStyles.rel = "stylesheet";
  brandStyles.href = "/static/brand-lockup.css";
  document.head.append(brandStyles);
  const brand = document.querySelector(".site-nav .brand");
  if (brand) {
    brand.classList.add("brand-lockup");
    brand.setAttribute("aria-label", "SYLRIX — Reborn. Reforged. Relentless.");
    brand.innerHTML = '<img src="/static/assets/sylrix-brand-lockup-v2.png" alt="SYLRIX — Reborn. Reforged. Relentless.">';
  }
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
  const gallery = document.querySelector(".training-cards");
  if (gallery && gallery.children.length < 8) {
    [{name: "Powerlifting", path: "powerlifting", detail: "Build the total.", image: "mode-strength"}, {name: "CrossFit", path: "crossfit", detail: "Train work capacity.", image: "mode-general"}].forEach((item) => {
      const card = document.createElement("article");
      card.className = `mode-card ${item.image}`;
      card.tabIndex = 0;
      card.setAttribute("role", "link");
      card.innerHTML = `<strong>${item.name}</strong><span>${item.detail}</span>`;
      const open = () => { window.location.href = `/training/${item.path}`; };
      card.addEventListener("click", open);
      card.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); open(); } });
      gallery.append(card);
    });
  }
});
