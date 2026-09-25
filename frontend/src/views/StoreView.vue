<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { storeApi, type Product, type Store } from "@/api/store";
import { ordersApi } from "@/api/orders";
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();
const isAdmin = computed(() => userStore.isAdmin);
const shopStores = computed(() => stores.value.filter((s) => s.store_type === "shop" || s.store_type === "supplier" || !s.store_type));

const sortedProducts = computed(() => {
  const arr = [...products.value];
  arr.sort((a, b) => {
    if (sortBy.value === "price") return (a.price ?? 1e12) - (b.price ?? 1e12);
    if (sortBy.value === "stock") return (b.stock ?? 0) - (a.stock ?? 0);
    return (b.store_rating ?? 0) - (a.store_rating ?? 0);
  });
  return arr;
});

const groupedByStore = computed(() => {
  const map = new Map<string, { storeName: string; rating: number | null; phone: string | null; city: string | null; items: Product[] }>();
  for (const p of sortedProducts.value) {
    const key = String(p.store_id ?? "none");
    if (!map.has(key)) {
      map.set(key, {
        storeName: p.store_name || "未标注门店",
        rating: p.store_rating ?? null,
        phone: p.store_phone ?? null,
        city: p.store_city ?? null,
        items: [],
      });
    }
    map.get(key)!.items.push(p);
  }
  return [...map.values()];
});

const products = ref<Product[]>([]);
const stores = ref<Store[]>([]);
const category = ref("");
const keyword = ref("");
const storeFilter = ref<number | "">("");
const browseMode = ref<"store" | "flat">("store");
const sortBy = ref<"rating" | "price" | "stock">("rating");
const loading = ref(false);

const CATEGORIES = [
  { value: "", label: "全部" },
  { value: "cage", label: "笼子" },
  { value: "toy", label: "玩具" },
  { value: "supply", label: "用品" },
  { value: "food", label: "食品" },
  { value: "health", label: "医疗保健" },
];
const catLabel = (v: string) => CATEGORIES.find((c) => c.value === v)?.label ?? v;
const speciesLabel = (v: string) =>
  ({ dog: "犬", cat: "猫", both: "通用" } as Record<string, string>)[v] ?? v;

async function fetchProducts() {
  loading.value = true;
  try {
    products.value = await storeApi.products({
      category: category.value || undefined,
      keyword: keyword.value || undefined,
      store_id: storeFilter.value || undefined,
    });
  } finally {
    loading.value = false;
  }
}

// ---- 商品管理（超管） ----
const showProductDialog = ref(false);
const saving = ref(false);
const editingPid = ref<number | null>(null);
const pform = ref({
  name: "",
  category: "cage",
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

function openAddProduct() {
  editingPid.value = null;
  pform.value = {
    name: "",
    category: "cage",
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
    is_active: p.is_active,
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
  saving.value = true;
  try {
    if (editingPid.value) {
      await storeApi.updateProduct(editingPid.value, { ...pform.value });
      ElMessage.success("已更新");
    } else {
      await storeApi.createProduct({ ...pform.value });
      ElMessage.success("商品已上架");
    }
    showProductDialog.value = false;
    await fetchProducts();
  } finally {
    saving.value = false;
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
  await fetchProducts();
}

// ---- 门店管理（超管） ----
const showStoreDialog = ref(false);
const savingStore = ref(false);
const sform = ref({
  name: "",
  store_type: "shop",
  address: "",
  phone: "",
  description: "",
});

const STORE_TYPES = [
  { value: "shop", label: "宠物店" },
  { value: "hospital", label: "宠物医院" },
  { value: "boarding", label: "寄养中心" },
];
const storeTypeLabel = (v: string) => STORE_TYPES.find((x) => x.value === v)?.label ?? v;

async function fetchStores() {
  stores.value = await storeApi.stores();
}

function openAddStore() {
  sform.value = { name: "", store_type: "shop", address: "", phone: "", description: "" };
  showStoreDialog.value = true;
}

async function saveStore() {
  if (!sform.value.name.trim()) {
    ElMessage.warning("请输入门店名称");
    return;
  }
  savingStore.value = true;
  try {
    await storeApi.createStore({ ...sform.value });
    ElMessage.success("门店已添加");
    showStoreDialog.value = false;
    await fetchStores();
  } finally {
    savingStore.value = false;
  }
}

async function removeStore(s: Store) {
  await ElMessageBox.confirm(`确定删除门店「${s.name}」？其下商品将一并删除。`, "删除确认", {
    type: "warning",
    confirmButtonText: "删除",
    cancelButtonText: "取消",
    confirmButtonClass: "el-button--danger",
  });
  await storeApi.removeStore(s.id);
  ElMessage.success("已删除");
  await fetchStores();
}

onMounted(() => {
  fetchProducts();
  fetchStores();
});

const buyP = ref<Product | null>(null);
const buyQty = ref(1);
const buyAddr = ref("");
const buying = ref(false);

function openBuy(p: Product) {
  buyP.value = p;
  buyQty.value = 1;
  buyAddr.value = "";
}

async function submitBuy() {
  if (!buyP.value || !buyAddr.value.trim()) {
    ElMessage.warning("请填写配送地址");
    return;
  }
  buying.value = true;
  try {
    await ordersApi.create({
      items: [{ product_id: buyP.value.id, qty: buyQty.value }],
      address: buyAddr.value.trim(),
      shipping_mode: buyP.value.shipping_mode,
    });
    ElMessage.success({
      message: "下单成功，可在「我的订单」查看进度",
      duration: 3500,
    });
    buyP.value = null;
    await fetchProducts();
  } finally {
    buying.value = false;
  }
}
</script>

<template>
  <div class="page-container">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <div>
        <h2 class="page-title" style="margin: 0 0 4px">宠物用品商城</h2>
        <p class="page-sub" style="margin: 0">
          像美团点外卖一样按店逛：比品牌、包装、库存与配送。下单后由该宠物店履约（语音提醒店员）。
        </p>
      </div>
      <div v-if="isAdmin" style="display: flex; gap: 8px">
        <el-button @click="showStoreDialog = true">
          <el-icon style="margin-right: 4px"><OfficeBuilding /></el-icon>门店管理
        </el-button>
      </div>
    </div>

    <!-- 筛选 -->
    <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap">
      <el-radio-group v-model="category" @change="fetchProducts">
        <el-radio-button v-for="c in CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</el-radio-button>
      </el-radio-group>
      <el-select v-model="storeFilter" clearable placeholder="按宠物店筛选" style="width: 200px" @change="fetchProducts">
        <el-option v-for="s in shopStores" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
      <el-radio-group v-model="browseMode" size="small">
        <el-radio-button value="store">按门店逛</el-radio-button>
        <el-radio-button value="flat">全部商品</el-radio-button>
      </el-radio-group>
      <el-select v-model="sortBy" style="width: 150px">
        <el-option label="按门店评分" value="rating" />
        <el-option label="按价格" value="price" />
        <el-option label="按库存" value="stock" />
      </el-select>
      <el-input
        v-model="keyword"
        placeholder="搜索商品名称"
        clearable
        style="width: 220px"
        @keyup.enter="fetchProducts"
        @clear="fetchProducts"
      >
        <template #append>
          <el-button @click="fetchProducts"><el-icon><Search /></el-icon></el-button>
        </template>
      </el-input>
    </div>

    <div v-loading="loading" style="min-height: 200px">
      <el-empty v-if="!loading && !products.length" description="暂无在售商品" :image-size="90" />
      <template v-else-if="browseMode === 'store'">
        <div v-for="g in groupedByStore" :key="g.storeName" style="margin-bottom: 24px">
          <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px">
            <h3 style="margin: 0; font-size: 16px">{{ g.storeName }}</h3>
            <span class="text-muted" style="font-size: 12px">评分 {{ g.rating ?? "—" }} · {{ g.city || "" }} · {{ g.phone || "暂无电话" }}</span>
          </div>
          <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px">
            <div v-for="p in g.items" :key="p.id" class="card" style="padding: 0; overflow: hidden; display: flex; flex-direction: column">
              <div style="height: 140px; background: #f3f4f6">
                <img
                  v-if="p.image_url"
                  :src="p.image_url"
                  :alt="p.name"
                  style="width: 100%; height: 100%; object-fit: cover; display: block"
                  loading="lazy"
                />
              </div>
              <div style="padding: 14px 16px 16px; display: flex; flex-direction: column; flex: 1">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px">
                <el-tag size="small" effect="plain">{{ catLabel(p.category) }}</el-tag>
                <el-tag v-if="p.brand" size="small" type="warning" effect="plain">{{ p.brand }}</el-tag>
              </div>
              <div style="font-size: 15px; font-weight: 600; margin-bottom: 4px">{{ p.name }}</div>
              <div class="text-muted" style="font-size: 12px; margin-bottom: 8px">
                {{ speciesLabel(p.species) }}
                <template v-if="p.package_spec"> · 包装 {{ p.package_spec }}</template>
                <template v-if="p.spec"> · {{ p.spec }}</template>
              </div>
              <p class="text-secondary" style="font-size: 12px; margin: 0 0 8px; flex: 1">{{ p.description || "—" }}</p>
              <div class="text-muted" style="font-size: 12px; margin-bottom: 8px">
                库存 {{ p.stock ?? "—" }} · {{ p.shipping_mode === "express" ? "快递" : "同城即时" }}
                <span v-if="p.promo"> · {{ p.promo }}</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span style="font-size: 18px; font-weight: 700; color: #d97706">
                  {{ p.price != null ? `¥${p.price}` : "面议" }}
                </span>
                <el-button size="small" type="primary" @click="openBuy(p)">向该店下单</el-button>
              </div>
              </div>
            </div>
          </div>
        </div>
      </template>
      <div v-else style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px">
        <div v-for="p in sortedProducts" :key="p.id" class="card" style="padding: 16px; display: flex; flex-direction: column">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px">
            <el-tag size="small" effect="plain">{{ catLabel(p.category) }}</el-tag>
            <el-tag v-if="!p.is_active" size="small" type="info" effect="plain">已下架</el-tag>
          </div>
          <div style="font-size: 15px; font-weight: 600; margin-bottom: 4px">{{ p.name }}</div>
          <div class="text-muted" style="font-size: 12px; margin-bottom: 8px">
            {{ p.brand ? p.brand + " · " : "" }}{{ speciesLabel(p.species) }}
            <template v-if="p.package_spec"> · {{ p.package_spec }}</template>
            <template v-if="p.spec"> · {{ p.spec }}</template>
          </div>
          <p class="text-secondary" style="font-size: 12px; margin: 0 0 8px; flex: 1">{{ p.description || "—" }}</p>
          <div class="text-muted" style="font-size: 12px; margin-bottom: 8px">
            {{ p.store_name || "未标注门店" }}
            <span v-if="p.store_phone"> · {{ p.store_phone }}</span>
            · 评分 {{ p.store_rating ?? "—" }}
            · 库存 {{ p.stock ?? "—" }}
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span style="font-size: 18px; font-weight: 700; color: #d97706">
              {{ p.price != null ? `¥${p.price}` : "面议" }}
            </span>
            <div>
              <el-button size="small" type="primary" @click="openBuy(p)">向该店下单</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 商品对话框 -->
    <el-dialog v-model="showProductDialog" :title="editingPid ? '编辑商品' : '上架商品'" width="560px">
      <el-form label-position="top">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
          <el-form-item label="商品名称" required>
            <el-input v-model="pform.name" maxlength="60" />
          </el-form-item>
          <el-form-item label="分类">
            <el-select v-model="pform.category" style="width: 100%">
              <el-option v-for="c in CATEGORIES.slice(1)" :key="c.value" :label="c.label" :value="c.value" />
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
            <el-input v-model="pform.brand" placeholder="如：皇家、渴望" />
          </el-form-item>
          <el-form-item label="包装规格">
            <el-input v-model="pform.package_spec" placeholder="如：1.5kg / 10kg 袋装" />
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
        <el-button type="primary" :loading="saving" @click="saveProduct">保存</el-button>
      </template>
    </el-dialog>

    <!-- 门店管理对话框 -->
    <el-dialog v-model="showStoreDialog" title="门店管理" width="560px">
      <div style="display: flex; gap: 8px; margin-bottom: 12px">
        <el-input v-model="sform.name" placeholder="新门店名称" style="flex: 1" maxlength="40" />
        <el-select v-model="sform.store_type" style="width: 110px">
          <el-option v-for="t in STORE_TYPES" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-button type="primary" :loading="savingStore" @click="saveStore">添加</el-button>
      </div>
      <el-table :data="stores" style="width: 100%">
        <el-table-column prop="name" label="名称" min-width="120" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">{{ storeTypeLabel(row.store_type) }}</template>
        </el-table-column>
        <el-table-column prop="address" label="地址" min-width="140">
          <template #default="{ row }">{{ row.address || "—" }}</template>
        </el-table-column>
        <el-table-column prop="phone" label="电话" width="110">
          <template #default="{ row }">{{ row.phone || "—" }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="right">
          <template #default="{ row }">
            <el-button size="small" type="danger" link @click="removeStore(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!stores.length" description="暂无门店" :image-size="60" />
    </el-dialog>

    <el-dialog :model-value="!!buyP" title="确认下单" width="420px" @close="buyP = null">
      <div v-if="buyP">
        <p>{{ buyP.name }} · {{ buyP.store_name }}（向该店下单，平台不自营）</p>
        <p v-if="buyP.brand" class="text-muted" style="font-size: 13px">{{ buyP.brand }} {{ buyP.package_spec }}</p>
        <el-form-item label="数量"><el-input-number v-model="buyQty" :min="1" :max="buyP.stock || 99" /></el-form-item>
        <el-form-item label="配送地址"><el-input v-model="buyAddr" type="textarea" :rows="2" /></el-form-item>
      </div>
      <template #footer>
        <el-button @click="buyP = null">取消</el-button>
        <el-button type="primary" :loading="buying" @click="submitBuy">提交订单</el-button>
      </template>
    </el-dialog>
  </div>
</template>
