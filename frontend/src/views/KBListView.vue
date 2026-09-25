<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { useKbStore } from "@/stores/kb";

const kbStore = useKbStore();
const router = useRouter();

const keyword = ref("");
const showDialog = ref(false);
const creating = ref(false);
const form = ref({ name: "", description: "" });

const filtered = computed(() => {
  const k = keyword.value.trim().toLowerCase();
  if (!k) return kbStore.kbs;
  return kbStore.kbs.filter((kb) => kb.name.toLowerCase().includes(k));
});

function create() {
  if (!form.value.name.trim()) {
    ElMessage.warning("请输入知识库名称");
    return;
  }
  creating.value = true;
  kbStore
    .create(form.value.name.trim(), form.value.description.trim())
    .then(() => {
      ElMessage.success("知识库创建成功");
      showDialog.value = false;
      form.value = { name: "", description: "" };
    })
    .finally(() => (creating.value = false));
}

async function remove(kb: { id: number; name: string }) {
  await ElMessageBox.confirm(
    `确定删除知识库「${kb.name}」？其中所有文档将一并删除，且不可恢复。`,
    "删除确认",
    { type: "warning", confirmButtonText: "删除", cancelButtonText: "取消", confirmButtonClass: "el-button--danger" }
  );
  await kbStore.remove(kb.id);
  ElMessage.success("已删除");
}

onMounted(() => kbStore.fetchKbs());
</script>

<template>
  <div class="page-container">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <h2 class="page-title" style="margin: 0">知识库</h2>
      <div style="display: flex; gap: 12px">
        <el-input v-model="keyword" placeholder="搜索知识库" clearable style="width: 240px" :prefix-icon="'Search'" />
        <el-button type="primary" @click="showDialog = true">
          <el-icon style="margin-right: 4px"><Plus /></el-icon>新建知识库
        </el-button>
      </div>
    </div>

    <div v-loading="kbStore.loading" style="min-height: 200px">
      <!-- 卡片网格 -->
      <div v-if="filtered.length" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px">
        <div v-for="kb in filtered" :key="kb.id" class="card" style="display: flex; flex-direction: column; transition: box-shadow .2s" @mouseenter="($event.currentTarget as HTMLElement).style.boxShadow = 'var(--app-shadow-lg)'" @mouseleave="($event.currentTarget as HTMLElement).style.boxShadow = 'var(--app-shadow)'">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px">
            <div style="width: 38px; height: 38px; border-radius: 10px; background: #2563eb18; color: #2563eb; display: flex; align-items: center; justify-content: center">
              <el-icon :size="20"><FolderOpened /></el-icon>
            </div>
            <div style="flex: 1; min-width: 0">
              <div style="font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: flex; align-items: center; gap: 6px">
                <el-icon v-if="kb.is_public" color="#d97706"><Lock /></el-icon>
                <span>{{ kb.name }}</span>
                <el-tag v-if="kb.is_public" size="small" type="warning" effect="plain">公共</el-tag>
              </div>
              <div class="text-muted" style="font-size: 12px">{{ kb.created_at.slice(0, 10) }}</div>
            </div>
          </div>
          <p class="text-secondary" style="flex: 1; font-size: 13px; line-height: 1.6; margin: 0 0 14px; min-height: 40px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical">
            {{ kb.description || "暂无描述" }}
          </p>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <el-tag size="small" effect="plain">文档 {{ kb.doc_count ?? "-" }}</el-tag>
            <div>
              <el-button size="small" type="primary" plain @click="router.push(`/kb/${kb.id}/documents`)">查看</el-button>
              <el-tooltip v-if="kb.is_public" content="公共知识库为系统资源，不可删除">
                <span>
                  <el-button size="small" type="danger" link disabled>删除</el-button>
                </span>
              </el-tooltip>
              <el-button v-else size="small" type="danger" link @click="remove(kb)">删除</el-button>
            </div>
          </div>
        </div>
      </div>

      <el-empty v-else-if="!kbStore.loading" description="暂无知识库，点击右上角新建">
        <el-button type="primary" @click="showDialog = true">新建知识库</el-button>
      </el-empty>
    </div>

    <!-- 新建对话框 -->
    <el-dialog v-model="showDialog" title="新建知识库" width="440px">
      <el-form label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：企业研发文档库" maxlength="50" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="简要描述该知识库的用途（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>