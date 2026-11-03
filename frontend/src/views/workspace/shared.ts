/** 工作台各面板共用的文案与状态映射，与拆分前 WorkspaceView 保持一致。 */

export const STORE_TYPES: Record<string, string> = {
  shop: "宠物店",
  hospital: "宠物医院",
  boarding: "寄养中心",
};

export const APPT_TYPES: Record<string, string> = {
  exam: "就诊",
  grooming: "美容",
  boarding: "寄养",
  consult: "咨询",
};

export const STATUS: Record<string, { label: string; type: "primary" | "success" | "warning" | "info" | "danger" }> = {
  pending: { label: "待处理", type: "warning" },
  confirmed: { label: "已确认", type: "primary" },
  completed: { label: "已完成", type: "success" },
  cancelled: { label: "已取消", type: "info" },
};

export const statusLabel = (s: string) => STATUS[s]?.label ?? s;
export const statusType = (s: string) => STATUS[s]?.type ?? "info";

export const CATEGORIES = [
  { value: "cage", label: "笼子" },
  { value: "toy", label: "玩具" },
  { value: "supply", label: "用品" },
  { value: "food", label: "食品" },
  { value: "health", label: "医疗保健" },
];

export const catLabel = (v: string) => CATEGORIES.find((c) => c.value === v)?.label ?? v;

export const speciesLabel = (v: string) =>
  ({ dog: "犬", cat: "猫", both: "通用" } as Record<string, string>)[v] ?? v;

export const fmtDate = (v: string | null) =>
  v ? new Date(v).toLocaleString("zh-CN", { hour12: false }).slice(0, 16) : "—";
