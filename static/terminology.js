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
});
