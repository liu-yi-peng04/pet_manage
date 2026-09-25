import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import "element-plus/dist/index.css";
import * as ElementPlusIcons from "@element-plus/icons-vue";

import App from "./App.vue";
import router from "./router";
import "./styles/theme.css";

const app = createApp(App);

// 全局注册 Element Plus 图标
for (const [name, comp] of Object.entries(ElementPlusIcons)) {
  app.component(name, comp as never);
}

app.use(createPinia());
app.use(router);
app.use(ElementPlus, { locale: zhCn });
app.mount("#app");