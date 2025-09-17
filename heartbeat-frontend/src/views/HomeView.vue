<template>
  <div class="home-container">
    <!-- 顶部导航栏 -->
    <van-nav-bar title="与ta的约定" safe-area-inset-top>
      <template #right>
        <van-icon name="setting-o" size="18" @click="goToSettings" />
      </template>
    </van-nav-bar>

    <!-- 任务列表 -->
    <van-pull-refresh v-model="isRefreshing" @refresh="fetchTasks">
      <div class="task-list-container">
        <van-list
          v-if="tasks.length > 0"
          v-model:loading="isLoading"
          :finished="isFinished"
          finished-text="没有更多了"
          @load="onLoad"
          class="task-list"
        >
          <van-cell
            v-for="task in tasks"
            :key="task.id"
            :title="task.title"
            :label="task.description"
            is-link
            @click="goToTaskDetail(task.id)"
          />
        </van-list>
        
        <!-- 加载状态与空状态 -->
        <van-empty v-if="!isLoading && tasks.length === 0" description="还没有约定哦，快添加一个吧！" />
      </div>
    </van-pull-refresh>

    <!-- 悬浮按钮，用于添加新任务 -->
    <van-floating-bubble
      axis="xy"
      icon="plus"
      magnetic="x"
      @click="showCreateTaskDialog"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api'
import { showToast, showFailToast, showConfirmDialog } from 'vant'
import 'vant/es/toast/style';
import 'vant/es/dialog/style';
import 'vant/es/notify/style';


// --- 状态 & 响应式数据 ---
const router = useRouter()
const authStore = useAuthStore()

const tasks = ref([])
const isLoading = ref(false)
const isFinished = ref(false)
const isRefreshing = ref(false)
const error = ref(null)

// --- 方法 ---

const goToTaskDetail = (taskId) => {
  router.push({ name: 'task-detail', params: { id: taskId } });
};

// 跳转到设置页面
const goToSettings = () => {
  router.push('/settings')
}

// 获取任务列表
const fetchTasks = async () => {
  isLoading.value = true
  error.value = null
  try {
    const response = await apiClient.get('/tasks/')
    tasks.value = response.data
    isFinished.value = true // 假设我们一次性加载所有任务
  } catch (err) {
    error.value = err
    showFailToast('加载约定失败，请稍后重试')
    console.error('Failed to fetch tasks:', err)
  } finally {
    isLoading.value = false
    isRefreshing.value = false
  }
}

// Vant List 的 @load 事件处理器
const onLoad = () => {
  // 因为我们在 onMounted 中已经加载了所有数据，
  // 所以这里的 onLoad 可以暂时为空。
  // 如果未来需要分页加载，逻辑将在这里实现。
};

// 显示创建任务的对话框
const showCreateTaskDialog = () => {
  showConfirmDialog({
    title: '添加新约定',
    message: `
      <div style="text-align: left; padding: 10px 0;">
        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 5px; font-weight: bold;">标题：</label>
          <input id="task-title" type="text" placeholder="请输入约定标题" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box;" />
        </div>
        <div>
          <label style="display: block; margin-bottom: 5px; font-weight: bold;">描述：</label>
          <textarea id="task-description" placeholder="请输入约定描述" rows="3" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; resize: vertical;"></textarea>
        </div>
      </div>
    `,
    allowHtml: true,
    confirmButtonText: '创建',
    cancelButtonText: '取消',
    beforeClose: (action) => {
      if (action === 'confirm') {
        const title = document.getElementById('task-title')?.value?.trim();
        const description = document.getElementById('task-description')?.value?.trim();
        
        if (!title) {
          showFailToast('请输入约定标题');
          return false;
        }
        
        return handleCreateTask({ title, description });
      }
      return true;
    }
  });
};

// 处理创建任务的逻辑
const handleCreateTask = async (taskData) => {
  try {
    await apiClient.post('/tasks/', taskData);
    showToast('约定已添加');
    await fetchTasks(); // 成功后刷新列表
    return true; // 返回 true，让对话框关闭
  } catch (err) {
    showFailToast('添加失败，请重试');
    console.error('Failed to create task:', err);
    return false; // 返回 false，阻止对话框关闭
  }
};

// 退出登录
const logout = () => {
  authStore.logout()
  router.replace('/login')
  showToast('已退出')
}

// --- 生命周期钩子 ---
onMounted(() => {
  // 组件挂载后，自动获取任务列表
  fetchTasks()
})
</script>

<style scoped>
.home-container {
  padding-bottom: 20px;
}

.task-list {
  margin: 15px;
}

/* Vant Cell 样式覆盖 */
:deep(.van-cell) {
  margin-bottom: 10px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

/* Dialog 内部输入框的样式 */
:deep(.van-dialog__message) {
  text-align: left;
}
:deep(.van-field__control) {
  box-sizing: border-box;
  padding: 5px 8px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 14px;
}
</style>