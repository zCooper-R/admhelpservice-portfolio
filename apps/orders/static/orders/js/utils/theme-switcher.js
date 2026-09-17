function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
}

function toggleTheme() {
    const current = localStorage.getItem("theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);
}

document.addEventListener("DOMContentLoaded", () => {
    const storedTheme = localStorage.getItem("theme") || "dark";
    applyTheme(storedTheme);

    document.getElementById("theme-toggle").addEventListener("click", toggleTheme);
});
