'''<template>
  <div>
    <van-nav-bar
      title="设置"
      left-text="返回"
      left-arrow
      @click-left="onClickLeft"
    />
    <div class="settings-content">
      <div v-if="loading" class="loading-container">
        <van-loading size="24px">加载中...</van-loading>
      </div>
      <div v-else-if="error" class="error-container">
        <van-empty
          image="error"
          description="加载失败，请稍后重试"
        />
      </div>
      <div v-else-if="user">
        <!-- Connected Person Info -->
        <div v-if="user.partner" class="partner-info">
          <van-cell-group inset>
            <van-cell title="与ta的纪念" is-link @click="showPartnerInfo" />
          </van-cell-group>
        </div>

        <!-- Connect with Someone Form -->
        <div v-else class="bind-partner">
          <van-cell-group inset title="寻找ta">
            <van-field
              v-model="partnerCode"
              label="ta的邀请码"
              placeholder="请输入ta的邀请码"
            />
            <div class="bind-button-container">
              <van-button type="primary" block @click="bindPartner">确认连接</van-button>
            </div>
          </van-cell-group>
        </div>

        <!-- User Profile -->
        <van-cell-group inset title="个人信息">
          <van-cell title="用户名" :value="user.username" />
          <van-cell title="我的得分" :value="`${user.score || 0} 分`" />
          <van-cell title="退出登录" is-link @click="logout" />
        </van-cell-group>

        <!-- Score System (only show if has partner) -->
        <div v-if="user.partner" class="score-system">
          <van-cell-group inset title="得分系统">
            <van-cell title="我的得分" :value="`${user.score || 0} 分`" />
            <van-cell title="ta的得分" :value="`${user.partner.score || 0} 分`" />
            <van-cell title="申请加分" is-link @click="showScoreRequestDialog = true" />
            <van-cell title="得分申请记录" is-link @click="showScoreRequests" />
          </van-cell-group>
        </div>

        <!-- My Invitation Code -->
        <van-cell-group inset title="我的邀请码" class="invitation-code-group">
          <van-cell :value="user.invitation_code">
            <template #title>
              <span class="custom-title">邀请码</span>
            </template>
            <template #right-icon>
              <van-button size="small" type="primary" @click="copyCode">复制</van-button>
            </template>
          </van-cell>
        </van-cell-group>
        <!-- Task Management -->
        <van-cell-group inset title="任务管理">
          <van-field
            v-model="newTaskTitle"
            label="新任务"
            placeholder="输入任务名称"
          >
            <template #button>
              <van-button size="small" type="primary" @click="createTask" :loading="isCreating">添加</van-button>
            </template>
          </van-field>
          <div v-if="taskStore.tasks.length > 0">
            <van-cell v-for="task in taskStore.tasks" :key="task.id" :title="task.title">
              <template #right-icon>
                <van-switch :model-value="task.is_active" @update:model-value="status => toggleTaskStatus(task, status)" size="20px" />
              </template>
            </van-cell>
          </div>
          <van-empty v-else description="暂无任务，快去添加一个吧！" />
        </van-cell-group>
      </div>
    </div>

    <!-- Score Request Dialog -->
    <van-dialog
      v-model:show="showScoreRequestDialog"
      title="申请加分"
      show-cancel-button
      @confirm="submitScoreRequest"
    >
      <van-field
        v-model="scoreRequestPoints"
        label="申请分数"
        type="number"
        placeholder="请输入申请的分数"
      />
      <van-field
        v-model="scoreRequestReason"
        label="申请理由"
        type="textarea"
        rows="3"
        placeholder="请说明申请加分的理由"
      />
    </van-dialog>

    <!-- Score Requests List Dialog -->
    <van-dialog
      v-model:show="showScoreRequestsDialog"
      title="得分申请记录"
      :show-cancel-button="false"
      confirm-button-text="关闭"
    >
      <div class="score-requests-list">
        <div v-if="scoreRequests.length === 0" class="empty-requests">
          暂无申请记录
        </div>
        <div v-else>
          <div
            v-for="request in scoreRequests"
            :key="request.id"
            class="request-item"
          >
            <div class="request-header">
              <span class="request-type">
                {{ request.requester_id === user.id ? '我申请的' : '收到的申请' }}
              </span>
              <span class="request-status" :class="getStatusClass(request.status)">
                {{ getStatusText(request.status) }}
              </span>
            </div>
            <div class="request-content">
              <div class="request-info">
                <span>分数: {{ request.points }}分</span>
                <span>理由: {{ request.reason }}</span>
              </div>
              <div class="request-time">
                {{ formatTimestamp(request.timestamp) }}
              </div>
            </div>
            <div v-if="request.target_id === user.id && request.status === 'pending'" class="request-actions">
              <van-button size="small" type="success" @click="respondToRequest(request.id, 'approve')">
                同意
              </van-button>
              <van-button size="small" type="danger" @click="respondToRequest(request.id, 'reject')">
                拒绝
              </van-button>
            </div>
          </div>
        </div>
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '@/api'
import { useTaskStore } from '@/stores/tasks' // 引入 task store
import { useAuthStore } from '@/stores/auth' // 引入 auth store
import { showToast, showSuccessToast, showFailToast, showDialog } from 'vant'

const router = useRouter()
const loading = ref(true)
const error = ref(null)
const user = ref(null)
const partnerCode = ref('')
const taskStore = useTaskStore() // 初始化 task store
const authStore = useAuthStore() // 初始化 auth store
const newTaskTitle = ref('') // 新任务标题
const isCreating = ref(false) // 是否正在创建任务

// 得分系统相关状态
const showScoreRequestDialog = ref(false)
const showScoreRequestsDialog = ref(false)
const scoreRequestPoints = ref('')
const scoreRequestReason = ref('')
const scoreRequests = ref([])

const fetchUserInfo = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await apiClient.get('/users/me')
    user.value = response.data
  } catch (err) {
    error.value = '获取用户信息失败'
    showFailToast(error.value)
  } finally {
    loading.value = false
  }
}

const showPartnerInfo = () => {
  if (user.value && user.value.partner) {
    showDialog({
      title: '缘分的见证',
      message: `与 ${user.value.partner.username} 在 ${new Date(user.value.partner.bind_date).toLocaleDateString()} 结缘相识。`,
      theme: 'round-button',
    })
  }
}

const bindPartner = async () => {
  if (!partnerCode.value) {
    showToast('请输入邀请码')
    return
  }
  try {
    await apiClient.post('/users/bind_partner', {
      invitation_code: partnerCode.value,
    })
    showSuccessToast('连接成功！')
    await fetchUserInfo() // Refresh user info
  } catch (err) {
    const errorMessage = err.response?.data?.detail || '连接失败，请检查邀请码是否正确'
    showFailToast(errorMessage)
  }
}

const copyCode = async () => {
  try {
    await navigator.clipboard.writeText(user.value.invitation_code)
    showToast('邀请码已复制')
  } catch (err) {
    showFailToast('复制失败')
  }
}

const onClickLeft = () => {
  router.back()
}

// 退出登录
const logout = () => {
  authStore.logout()
  router.replace('/login')
  showToast('已退出')
}

// --- Task Management ---
const createTask = async () => {
  if (!newTaskTitle.value.trim()) {
    showToast('任务名称不能为空');
    return;
  }
  isCreating.value = true;
  try {
    await taskStore.createTask({ title: newTaskTitle.value, description: '' });
    newTaskTitle.value = '';
    showSuccessToast('任务添加成功！');
  } catch (error) {
    showFailToast('任务添加失败');
  } finally {
    isCreating.value = false;
  }
};

const toggleTaskStatus = async (task, newStatus) => {
  try {
    await taskStore.updateTask(task.id, { is_active: newStatus });
    showSuccessToast(`任务已${newStatus ? '启用' : '禁用'}`);
  } catch (error) {
    showFailToast('状态更新失败');
    // 状态更新失败时，需要将开关恢复原状
    task.is_active = !newStatus;
  }
};

// --- Score System Functions ---
const submitScoreRequest = async () => {
  if (!scoreRequestPoints.value || !scoreRequestReason.value.trim()) {
    showToast('请填写完整的申请信息')
    return
  }
  
  try {
    await apiClient.post('/score-requests/', {
      points: parseInt(scoreRequestPoints.value),
      reason: scoreRequestReason.value
    })
    
    showSuccessToast('申请提交成功！')
    scoreRequestPoints.value = ''
    scoreRequestReason.value = ''
    showScoreRequestDialog.value = false
  } catch (err) {
    const errorMessage = err.response?.data?.detail || '申请提交失败'
    showFailToast(errorMessage)
  }
}

const fetchScoreRequests = async () => {
  try {
    const response = await apiClient.get('/score-requests/')
    scoreRequests.value = response.data
  } catch (err) {
    showFailToast('获取申请记录失败')
  }
}

const showScoreRequests = async () => {
  await fetchScoreRequests()
  showScoreRequestsDialog.value = true
}

const respondToRequest = async (requestId, action) => {
  try {
    await apiClient.post(`/score-requests/${requestId}/respond`, {
      action: action
    })
    
    showSuccessToast(action === 'approve' ? '已同意申请' : '已拒绝申请')
    await fetchScoreRequests() // 刷新申请列表
    await fetchUserInfo() // 刷新用户信息（更新得分）
  } catch (err) {
    const errorMessage = err.response?.data?.detail || '操作失败'
    showFailToast(errorMessage)
  }
}

const getStatusText = (status) => {
  const statusMap = {
    'pending': '待处理',
    'approved': '已同意',
    'rejected': '已拒绝'
  }
  return statusMap[status] || status
}

const getStatusClass = (status) => {
  return `status-${status}`
}

const formatTimestamp = (timestamp) => {
  return new Date(timestamp).toLocaleString('zh-CN')
}


onMounted(async () => {
  await fetchUserInfo()
  await taskStore.fetchTasks() // 获取任务列表
})
</script>

<style scoped>
.settings-content {
  padding: 16px;
}
.bind-button-container {
  padding: 16px;
}
.loading-container, .error-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}
.invitation-code-group {
  margin-top: 20px;
  margin-bottom: 20px;
}

.score-requests-list {
  max-height: 400px;
  overflow-y: auto;
}

.request-item {
  border-bottom: 1px solid #eee;
  padding: 12px 0;
}

.request-item:last-child {
  border-bottom: none;
}

.request-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.request-type {
  font-weight: bold;
  color: #333;
}

.request-status {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.status-pending {
  background-color: #fff3cd;
  color: #856404;
}

.status-approved {
  background-color: #d4edda;
  color: #155724;
}

.status-rejected {
  background-color: #f8d7da;
  color: #721c24;
}

.request-content {
  margin-bottom: 8px;
}

.request-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 4px;
}

.request-time {
  font-size: 12px;
  color: #999;
}

.request-actions {
  display: flex;
  gap: 8px;
}

.empty-requests {
  text-align: center;
  color: #999;
  padding: 20px;
}
</style>
'''