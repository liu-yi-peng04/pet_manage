import { defineStore } from "pinia";
import { ref } from "vue";
import { kbApi } from "@/api/knowledge";
import type { KnowledgeBase } from "@/types";

export const useKbStore = defineStore("kb", () => {
  const kbs = ref<KnowledgeBase[]>([]);
  const loading = ref(false);

  async function fetchKbs() {
    loading.value = true;
    try {
      kbs.value = await kbApi.list();
    } finally {
      loading.value = false;
    }
  }

  async function create(name: string, description: string) {
    await kbApi.create({ name, description });
    await fetchKbs();
  }

  async function remove(id: number) {
    await kbApi.remove(id);
    await fetchKbs();
  }

  return { kbs, loading, fetchKbs, create, remove };
});