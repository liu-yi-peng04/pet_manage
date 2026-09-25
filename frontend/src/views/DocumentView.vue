<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { docApi } from "@/api/document";
import { kbApi } from "@/api/knowledge";
import { useUserStore } from "@/stores/user";
import type { DocumentItem } from "@/types";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const kbId = Number(route.params.id);

const kbName = ref("");
const kbPublic = ref(false);
const docs = ref<DocumentItem[]>([]);
const loading = ref(false);
const dragover = ref(false);
const uploading = ref(false);

// 可管理 = 本人私有库 或 超管操作公共库
const canManage = computed(() => !kbPublic.value || userStore.isAdmin);

interface UploadEntry {
  name: string;
  pct: number;
  status: "uploading" | "indexing" | "indexed" | "failed";
  error?: string;
}

// 上传队列：展示进度与状态
const uploads = ref<UploadEntry[]>([]);

const kbNameStore = ref("");

async function load() {
  loading.value = true;
  try {
    const kbs = await kbApi.list();
    const kb = kbs.find((k) => k.id === kbId);
    kbName.value = kb?.name ?? `知识库 #${kbId}`;
    kbPublic.value = kb?.is_public ?? false;
    kbNameStore.value = kb?.name ?? "";
    const list = await docApi.listByKb(kbId);
    docs.value = list;
  } finally {
    loading.value = false;
  }
}

function onFilePick(e: Event) {
  const files = (e.target as HTMLInputElement).files;
  if (files) uploadFiles(Array.from(files));
}

function onDrop(e: DragEvent) {
  dragover.value = false;
  const files = e.dataTransfer?.files;
  if (files && files.length) uploadFiles(Array.from(files));
}

async function uploadFiles(files: File[]) {
  if (!files.length) return;
  if (!canManage.value) {
    ElMessage.warning("公共知识库仅管理员可上传文档");
    return;
  }
  uploading.value = true;
  for (const f of files) {
    const entry: UploadEntry = { name: f.name, pct: 0, status: "indexing" };
    uploads.value.push(entry);
    try {
      const res = await docApi.upload(kbId, f, (pct) => {
        entry.pct = pct;
      });
      entry.status = res.status === "indexed" ? "indexed" : "indexing";
      entry.pct = 100;
      ElMessage.success(`「${f.name}」已入库`);
    } catch (e) {
      entry.status = "failed";
      entry.error = "上传失败";
    }
  }
  uploading.value = false;
  await load();
}

async function remove(doc: DocumentItem) {
  if (!canManage.value) {
    ElMessage.warning("公共知识库仅管理员可删除文档");
    return;
  }
  await docApi.remove(doc.id);
  ElMessage.success("已删除");
  await load();
}

const statusMeta: Record<string, { label: string; type: "success" | "danger" | "warning" | "info" }> = {
  indexed: { label: "已完成", type: "success" },
  failed: { label: "失败", type: "danger" },
  indexing: { label: "处理中", type: "warning" },
  uploading: { label: "上传中", type: "info" },
};

const tableDocs = computed(() => {
  const real = docs.value.map((d) => ({
    ...d,
    _label: statusMeta[d.status]?.label ?? d.status,
    _type: statusMeta[d.status]?.type ?? "info",
  }));
  // 合并进行中的上传项
  const pending = uploads.value.map((u, i) => ({
    id: -1000 - i,
    filename: u.name,
    file_type: u.name.split(".").pop() ?? "",
    status: u.status,
    created_at: "",
    _label: u.status === "indexed" ? "已完成" : u.status === "failed" ? "失败" : u.status === "indexing" ? "处理中" : `${u.pct}%`,
    _type: statusMeta[u.status]?.type ?? "info",
    _pct: u.pct,
  }));
  return [...pending, ...real];
});

onMounted(load);
</script>

<template>
  <div class="page-container">
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px">
      <el-button link @click="router.push('/kb')">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <h2 class="page-title" style="margin: 0">文档管理 · {{ kbName }}</h2>
    </div>

    <!-- 上传区（公共库仅管理员可见） -->
    <div
      v-if="canManage"
      :style="{
        border: `2px dashed ${dragover ? 'var(--app-primary)' : 'var(--app-border)'}`,
        borderRadius: 12,
        padding: '36px 20px',
        textAlign: 'center',
        background: dragover ? 'rgba(37,99,235,.04)' : 'var(--app-surface)',
        marginBottom: 20,
        cursor: 'pointer',
        transition: 'all .2s',
      }"
      @dragover.prevent="dragover = true"
      @dragleave.prevent="dragover = false"
      @drop.prevent="onDrop"
      @click="(($refs.fileInput as HTMLInputElement) || null)?.click()"
    >
      <el-icon :size="36" color="#2563eb"><UploadFilled /></el-icon>
      <p style="font-size: 15px; margin: 12px 0 4px">将文件拖拽到此处，或点击选择上传</p>
      <p class="text-muted" style="font-size: 12px; margin: 0">支持 PDF / DOCX / TXT / MD / MDX / CSV，可批量上传</p>
      <input ref="fileInput" type="file" multiple accept=".pdf,.docx,.txt,.md,.mdx,.markdown,.csv" style="display: none" @change="onFilePick" />
    </div>

    <!-- 上传进度列表 -->
    <div v-if="uploads.length" class="card" style="margin-bottom: 20px">
      <div style="font-weight: 600; margin-bottom: 12px">上传队列</div>
      <div v-for="(u, i) in uploads" :key="i" style="display: flex; align-items: center; gap: 12px; padding: 8px 0">
        <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ u.name }}</span>
        <el-progress :percentage="u.status === 'failed' ? 100 : u.pct" :status="u.status === 'failed' ? 'exception' : u.status === 'indexed' ? 'success' : undefined" style="width: 220px" />
      </div>
    </div>

    <!-- 文档表格 -->
    <div class="card">
      <el-table v-loading="loading" :data="tableDocs" stripe style="width: 100%">
        <el-table-column label="文件名" prop="filename" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px">
              <el-icon color="#2563eb"><Document /></el-icon>
              <span>{{ row.filename }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" prop="file_type" width="90">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ (row.file_type || "txt").toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-tag size="small" :type="row._type">{{ row._label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="160">
          <template #default="{ row }">
            <span class="text-secondary" style="font-size: 13px">{{ row.created_at ? row.created_at.slice(0, 19).replace("T", " ") : "-" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="danger" link :disabled="row.id < 0 || !canManage" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>