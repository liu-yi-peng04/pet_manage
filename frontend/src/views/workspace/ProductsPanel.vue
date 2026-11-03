<script setup lang="ts">
import { ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { workspaceApi } from "@/api/workspace";
import { storeApi, type Product } from "@/api/store";
import { CATEGORIES, catLabel, speciesLabel } from "./shared";

const products = ref<Product[]>([]);
const productLoading = ref(false);
const showProductDialog = ref(false);
const savingProduct = ref(false);
const editingPid = ref<number | null>(null);
const pform = ref({
  name: "",
  category: "supply",
  price: null as number | null,
  species: "both",
  min_weight_kg: null as number | null,
  max_weight_kg: null as number | null,
  spec: "",
  image_url: "",
  description: "",
  is_active: true,
  brand: "",
  package_spec: "",
});

const emit = defineEmits<{ changed: [] }>();

async function reload() {
  productLoading.value = true;
  try {
    products.value = await workspaceApi.products();
  } finally {
    productLoading.value = false;
  }
}

function openAddProduct() {
  editingPid.value = null;
  pform.value = {
    name: "",
    category: "supply",
    price: null,
    species: "both",
    min_weight_kg: null,
    max_weight_kg: null,
    spec: "",
    image_url: "",
    description: "",
    is_active: true,
    brand: "",
    package_spec: "",
  };
  showProductDialog.value = true;
}

function openEditProduct(p: Product) {
  editingPid.value = p.id;
  pform.value = {
    name: p.name,
    category: p.category,
    price: p.price,
    species: p.species,
    min_weight_kg: p.min_weight_kg,
    max_weight_kg: p.max_weight_kg,
    spec: p.spec ?? "",
    image_url: p.image_url ?? "",
    description: p.description,
    is_active: !!p.is_active,
    brand: p.brand ?? "",
    package_spec: p.package_spec ?? "",
  };
  showProductDialog.value = true;
}

async function saveProduct() {
  if (!pform.value.name.trim()) {
    ElMessage.warning("请输入商品名称");
    return;
  }
  savingProduct.value = true;
  try {
    if (editingPid.value) {
      await storeApi.updateProduct(editingPid.value, { ...pform.value });
      ElMessage.success("已更新");
    } else {
      await storeApi.createProduct({ ...pform.value });
      ElMessage.success("商品已上架");
    }
    showProductDialog.value = false;
    await reload();
    emit("changed");
  } finally {
    savingProduct.value = false;
  }
}

async function removeProduct(p: Product) {
  await ElMessageBox.confirm(`确定删除商品「${p.name}」？`, "删除确认", {
    type: "warning",
    confirmButtonText: "删除",
    cancelButtonText: "取消",
    confirmButtonClass: "el-button--danger",
  });
  await storeApi.removeProduct(p.id);
  ElMessage.success("已删除");
  await reload();
  emit("changed");
}

defineExpose({ reload });
</script>

<template>
  <div style="display: flex; justify-content: flex-end; margin-bottom: 12px">
    <el-button type="primary" size="small" @click="openAddProduct">
      <el-icon style="margin-right: 4px"><Plus /></el-icon>上架商品
    </el-button>
  </div>
  <el-table v-loading="productLoading" :data="products" style="width: 100%">
    <el-table-column prop="name" label="名称" min-width="160" />
    <el-table-column label="分类" width="100">
      <template #default="{ row }">{{ catLabel(row.category) }}</template>
    </el-table-column>
    <el-table-column label="价格" width="100">
      <template #default="{ row }">{{ row.price != null ? `¥${row.price}` : "面议" }}</template>
    </el-table-column>
    <el-table-column label="适用" width="90">
      <template #default="{ row }">{{ speciesLabel(row.species) }}</template>
    </el-table-column>
    <el-table-column label="规格" min-width="130">
      <template #default="{ row }">{{ row.spec || "—" }}</template>
    </el-table-column>
    <el-table-column label="状态" width="90">
      <template #default="{ row }">
        <el-tag size="small" :type="row.is_active ? 'success' : 'info'" effect="plain">
          {{ row.is_active ? "在售" : "下架" }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="120" align="right">
      <template #default="{ row }">
        <el-button size="small" link @click="openEditProduct(row)">编辑</el-button>
        <el-button size="small" type="danger" link @click="removeProduct(row)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>
  <el-empty v-if="!productLoading && !products.length" description="本店暂无商品" :image-size="70" />

  <el-dialog v-model="showProductDialog" :title="editingPid ? '编辑商品' : '上架商品'" width="560px">
    <el-form label-position="top">
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
        <el-form-item label="商品名称" required>
          <el-input v-model="pform.name" maxlength="60" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="pform.category" style="width: 100%">
            <el-option v-for="c in CATEGORIES" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="价格 (元)">
          <el-input-number v-model="pform.price" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="适用物种">
          <el-select v-model="pform.species" style="width: 100%">
            <el-option label="通用" value="both" />
            <el-option label="犬" value="dog" />
            <el-option label="猫" value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item label="适用体重下限 (kg)">
          <el-input-number v-model="pform.min_weight_kg" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="适用体重上限 (kg)">
          <el-input-number v-model="pform.max_weight_kg" :min="0" style="width: 100%" />
        </el-form-item>
      </div>
      <el-form-item label="规格参数">
        <el-input v-model="pform.spec" placeholder="如：长 90cm × 宽 60cm × 高 65cm" />
      </el-form-item>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
        <el-form-item label="品牌">
          <el-input v-model="pform.brand" placeholder="如：皇家" />
        </el-form-item>
        <el-form-item label="包装">
          <el-input v-model="pform.package_spec" placeholder="如：10kg 袋装" />
        </el-form-item>
      </div>
      <el-form-item label="商品描述">
        <el-input v-model="pform.description" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="上架状态">
        <el-switch v-model="pform.is_active" active-text="上架" inactive-text="下架" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showProductDialog = false">取消</el-button>
      <el-button type="primary" :loading="savingProduct" @click="saveProduct">保存</el-button>
    </template>
  </el-dialog>
</template>
