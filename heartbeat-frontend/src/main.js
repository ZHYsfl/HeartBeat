import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

// 1. 引入 Vant 组件库和样式
import Vant from 'vant';
import 'vant/lib/index.css';

const app = createApp(App)

app.use(createPinia())
app.use(router)

// 2. 全局注册 Vant
app.use(Vant);

app.mount('#app')
