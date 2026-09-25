import { defineStore } from "pinia";
import { ref } from "vue";

export const useAppStore = defineStore("app", () => {
  const isDark = ref<boolean>(localStorage.getItem("theme") === "dark");
  const sidebarCollapsed = ref<boolean>(false);

  function toggleTheme() {
    isDark.value = !isDark.value;
    localStorage.setItem("theme", isDark.value ? "dark" : "light");
    applyTheme();
  }

  function applyTheme() {
    const root = document.documentElement;
    root.classList.toggle("dark", isDark.value);
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value;
  }

  return { isDark, sidebarCollapsed, toggleTheme, applyTheme, toggleSidebar };
});