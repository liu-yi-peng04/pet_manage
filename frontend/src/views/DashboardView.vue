<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useKbStore } from "@/stores/kb";
import { docApi } from "@/api/document";
import type { DocumentItem } from "@/types";

const kbStore = useKbStore();
const router = useRouter();

const docList = ref<DocumentItem[]>([]);
const kbCount = ref(0);
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    await kbStore.fetchKbs();
    kbCount.value = kbStore.kbs.length;
    docList.value = await docApi.listAll();
  } finally {
    loading.value = false;
  }
}

const indexedDocs = () => docList.value.filter((d) => d.status === "indexed").length;
const totalDoc = () => docList.value.length;

onMounted(load);

const stats = [
  {
    title: "知识库数量",
    value: () => kbCount.value,
    icon: "Collection",
    color: "#2563eb",
    path: "/kb",
  },
  {
    title: "文档数量",
    value: totalDoc,
    icon: "Document",
    color: "#059669",
    path: "/kb",
  },
  {
    title: "已入库文档",
    value: indexedDocs,
    icon: "Finished",
    color: "#d97706",
    path: "/kb",
  },
];

function recentDocs() {
  return [...docList.value].sort((a, b) => (a.created_at < b.created_at ? 1 : -1)).slice(0, 6);
}
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">工作台</h2>

    <!-- 统计卡片 -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 20px">
      <div v-for="s in stats" :key="s.title" class="card" style="display: flex; align-items: center; gap: 16px; cursor: pointer" @click="router.push(s.path)">
        <div :style="{ width: 48, height: 48, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', background: `${s.color}18`, color: s.color }">
          <el-icon :size="26"><component :is="s.icon" /></el-icon>
        </div>
        <div>
          <div style="font-size: 26px; font-weight: 700; line-height: 1.2">{{ s.value() }}</div>
          <div class="text-secondary" style="font-size: 13px">{{ s.title }}</div>
        </div>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start">
      <!-- 最近知识库 -->
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
          <span style="font-weight: 600">我的知识库</span>
          <el-button link type="primary" @click="router.push('/kb')">管理</el-button>
        </div>
        <div v-if="!kbStore.kbs.length" class="text-muted" style="padding: 24px 0; text-align: center">暂无知识库，去创建一个吧</div>
        <div v-else style="display: flex; flex-direction: column; gap: 10px">
          <div v-for="kb in kbStore.kbs" :key="kb.id" style="display: flex; align-items: center; justify-content: space-between; padding: 12px; border: 1px solid var(--app-border); border-radius: 8px; cursor: pointer" @click="router.push(`/kb/${kb.id}/documents`)">
            <div style="display: flex; align-items: center; gap: 10px">
              <el-icon color="#2563eb"><FolderOpened /></el-icon>
              <span>{{ kb.name }}</span>
            </div>
            <el-tag size="small" effect="plain">{{ kb.created_at.slice(0, 10) }}</el-tag>
          </div>
        </div>
      </div>

      <!-- 最近文档 -->
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
          <span style="font-weight: 600">最近文档</span>
        </div>
        <div v-if="!recentDocs().length" class="text-muted" style="padding: 24px 0; text-align: center">暂无文档</div>
        <div v-else style="display: flex; flex-direction: column; gap: 10px">
          <div v-for="d in recentDocs()" :key="d.id" style="display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--app-border)">
            <el-icon color="#059669"><Document /></el-icon>
            <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ d.filename }}</span>
            <el-tag size="small" :type="d.status === 'indexed' ? 'success' : d.status === 'failed' ? 'danger' : 'warning'">
              {{ d.status === 'indexed' ? '已入库' : d.status === 'failed' ? '失败' : '处理中' }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 图表占位（后端暂未提供统计接口） -->
    <div class="card" style="margin-top: 16px">
      <span style="font-weight: 600">问答 / 活跃趋势</span>
      <el-empty description="趋势图表需后端统计接口，暂未接入" :image-size="80" style="padding: 30px 0" />
    </div>
  </div>
</template>