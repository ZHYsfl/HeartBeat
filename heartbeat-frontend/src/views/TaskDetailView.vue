<template>
  <div class="task-detail-view">
    <van-nav-bar
      :title="task ? task.title : '加载中...'"
      left-arrow
      @click-left="goBack"
    />
    <div v-if="loading" class="loading-container">
      <van-loading size="24px">加载中...</van-loading>
    </div>
    <div v-else-if="error" class="error-container">
      <van-empty image="error" :description="error" />
    </div>
    <div v-else-if="task" class="task-content">
      <van-cell-group inset>
        <van-cell title="约定标题" :value="task.title" />
        <van-cell title="约定描述" :label="task.description" />
        <van-cell title="创建者" :value="task.creator ? task.creator.username : '未知用户'" />
         <van-cell title="状态" :value="task.is_active ? '进行中' : '已禁用'" />
      </van-cell-group>

      <van-divider>打卡记录</van-divider>

        <div class="check-in-list">
            <van-pull-refresh v-model="isRefreshing" @refresh="onRefresh">
                <van-empty v-if="!checkIns.length" description="还没有人打卡，快来第一个吧！" />
                <van-list
                    v-else
                    v-model:loading="isListLoading"
                    :finished="true"
                    finished-text="没有更多了"
                >
                    <div 
                        v-for="checkIn in checkIns" 
                        :key="checkIn.id" 
                        class="check-in-card"
                    >
                        <van-cell 
                            :title="`${checkIn.user ? checkIn.user.username : '未知用户'} 的打卡`"
                            :label="checkIn.text || '没有留下任何文字'"
                            @click="showCheckInDetail(checkIn)"
                        >
                            <template #value>
                                <div class="check-in-meta">
                                    <span>{{ formatTimestamp(checkIn.timestamp) }}</span>
                                    <div v-if="checkIn.image_url" class="images-container">
                                        <van-image
                                            v-for="(imageUrl, index) in getImageUrls(checkIn.image_url)"
                                            :key="index"
                                            width="60"
                                            height="60"
                                            :src="getImageUrl(imageUrl)"
                                            fit="cover"
                                            radius="8"
                                            style="margin-top: 8px; margin-right: 8px; cursor: pointer;"
                                            @click.stop="previewImages(checkIn.image_url, index)"
                                        />
                                    </div>
                                </div>
                            </template>
                        </van-cell>
                        
                        <!-- 评论和点赞区域 -->
                        <div class="interaction-area">
                            <!-- 点赞按钮 -->
                            <div class="like-section">
                                <van-button 
                                    :type="checkIn.userLiked ? 'primary' : 'default'"
                                    size="small"
                                    icon="good-job-o"
                                    @click="toggleLike(checkIn)"
                                    :loading="checkIn.likingLoading"
                                >
                                    {{ checkIn.likeCount || 0 }}
                                </van-button>
                            </div>
                            
                            <!-- 评论按钮 -->
                             <div class="comment-section">
                                 <van-button 
                                     type="default"
                                     size="small"
                                     icon="chat-o"
                                     @click="showCommentDialog(checkIn)"
                                     :disabled="checkIn.userCommented"
                                 >
                                     {{ checkIn.comments ? checkIn.comments.length : 0 }}
                                 </van-button>
                                 <span v-if="checkIn.userCommented" class="comment-status">已评论</span>
                             </div>
                        </div>
                        
                        <!-- 评论列表 -->
                        <div v-if="checkIn.comments && checkIn.comments.length > 0" class="comments-list">
                            <div 
                                v-for="comment in checkIn.comments" 
                                :key="comment.id"
                                class="comment-item"
                            >
                                <div class="comment-header">
                                    <span class="comment-author">{{ comment.user ? comment.user.username : '未知用户' }}</span>
                                    <span class="comment-time">{{ formatTimestamp(comment.timestamp) }}</span>
                                </div>
                                <div class="comment-content">{{ comment.content }}</div>
                            </div>
                        </div>
                    </div>
                </van-list>
            </van-pull-refresh>
        </div>

      <van-button
        type="primary"
        round
        icon="plus"
        class="check-in-button"
        @click="showCheckInDialog = true"
      >
        打卡
      </van-button>
    </div>

    <!-- 打卡对话框 -->
    <van-dialog
        v-model:show="showCheckInDialog"
        title="新的打卡"
        show-cancel-button
        @confirm="handleCheckIn"
    >
        <van-field
            v-model="checkInText"
            rows="2"
            autosize
            label="心情记录"
            type="textarea"
            maxlength="100"
            placeholder="分享一下此刻的想法吧..."
            show-word-limit
        />
        <van-field name="uploader" label="上传图片">
            <template #input>
                <van-uploader
                    v-model="fileList"
                    :max-count="3"
                    :after-read="afterRead"
                    @delete="deleteFile"
                    accept="image/*"
                    :preview-size="80"
                />
            </template>
        </van-field>
    </van-dialog>

    <!-- 评论对话框 -->
    <van-dialog
        v-model:show="showCommentDialogVisible"
        title="添加评论"
        show-cancel-button
        @confirm="handleAddComment"
        :confirm-button-loading="commentLoading"
    >
        <van-field
            v-model="newCommentText"
            rows="3"
            autosize
            label="评论内容"
            type="textarea"
            maxlength="200"
            placeholder="说点什么吧..."
            show-word-limit
        />
    </van-dialog>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { showNotify, showImagePreview } from 'vant';
import api from '@/api'; // 确保你有一个封装了axios的api模块
import { useAuthStore } from '@/stores/auth';

const route = useRoute();
const router = useRouter();
const taskId = ref(route.params.id);

const task = ref(null);
const checkIns = ref([]);
const loading = ref(true);
const error = ref(null);
const isRefreshing = ref(false);
const isListLoading = ref(false);

const showCheckInDialog = ref(false);
const checkInText = ref('');
const fileList = ref([]);
const uploadedFiles = ref([]);

// 评论相关状态
const showCommentDialogVisible = ref(false);
const newCommentText = ref('');
const currentCheckInForComment = ref(null);
const commentLoading = ref(false);

const goBack = () => router.back();

// 获取完整的图片 URL
const getImageUrl = (relativePath) => {
  // 注意：这里的 baseURL 需要根据你的后端服务地址进行配置
  const baseURL = 'http://localhost:8000';
  return `${baseURL}${relativePath}`;
};

// 解析多个图片URL
const getImageUrls = (imageUrlString) => {
  if (!imageUrlString) return [];
  return imageUrlString.split(',').filter(url => url.trim());
};


const fetchTaskDetails = async () => {
  try {
    const response = await api.get(`/tasks/${taskId.value}`);
    task.value = response.data;
  } catch (err) {
    error.value = '加载约定详情失败，请稍后重试。';
    showNotify({ type: 'danger', message: error.value });
  }
};

const fetchCheckIns = async () => {
    isListLoading.value = true;
    try {
        const response = await api.get(`/tasks/${taskId.value}/checkins`);
        checkIns.value = response.data;
        
        // 为每个打卡记录获取评论和点赞信息
        for (const checkIn of checkIns.value) {
            await fetchCommentsAndLikes(checkIn);
        }
    } catch (err) {
        showNotify({ type: 'danger', message: '加载打卡记录失败' });
    } finally {
        isListLoading.value = false;
    }
};

// 获取评论和点赞信息
const fetchCommentsAndLikes = async (checkIn) => {
    try {
        // 获取评论
        const commentsResponse = await api.get(`/checkins/${checkIn.id}/comments`);
        checkIn.comments = commentsResponse.data;
        
        // 获取点赞数量
        const likeCountResponse = await api.get(`/checkins/${checkIn.id}/likes/count`);
        checkIn.likeCount = likeCountResponse.data.count;
        
        // 获取点赞列表，检查当前用户是否已点赞
        const likesResponse = await api.get(`/checkins/${checkIn.id}/likes`);
        const currentUserId = getCurrentUserId(); // 需要实现获取当前用户ID的函数
        checkIn.userLiked = likesResponse.data.some(like => like.user_id === currentUserId);
        
        // 检查当前用户是否已评论
        checkIn.userCommented = checkIn.comments.some(comment => comment.user_id === currentUserId);
        
        // 初始化加载状态
        checkIn.likingLoading = false;
    } catch (err) {
        console.error('获取评论和点赞信息失败:', err);
        checkIn.comments = [];
        checkIn.likeCount = 0;
        checkIn.userLiked = false;
        checkIn.userCommented = false;
        checkIn.likingLoading = false;
    }
};

// 获取当前用户ID（这里需要根据你的认证系统实现）
const getCurrentUserId = () => {
    // 从认证store中获取用户ID
    const authStore = useAuthStore();
    return authStore.user?.id;
};

const onRefresh = async () => {
    isRefreshing.value = true;
    await fetchCheckIns();
    isRefreshing.value = false;
    showNotify({ type: 'success', message: '刷新成功' });
};

const handleCheckIn = async () => {
    if (!checkInText.value.trim()) {
        showNotify({ type: 'warning', message: '总得说点什么吧！' });
        return;
    }
    try {
        // multipart/form-data 格式
        const formData = new FormData();
        formData.append('text_content', checkInText.value);
        // 如果有图片，添加到 FormData
        if (uploadedFiles.value.length > 0) {
            uploadedFiles.value.forEach((file) => {
                formData.append('images', file);
            });
        }

        await api.post(`/tasks/${taskId.value}/checkin`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });

        showNotify({ type: 'success', message: '打卡成功！' });
        checkInText.value = ''; // 清空输入
        fileList.value = []; // 清空文件列表
        uploadedFiles.value = []; // 清空上传文件
        showCheckInDialog.value = false; // 关闭对话框
        await fetchCheckIns(); // 重新加载打卡记录
    } catch (err) {
        showNotify({ type: 'danger', message: '打卡失败，请稍后重试' });
    }
};

// 切换点赞状态
const toggleLike = async (checkIn) => {
    checkIn.likingLoading = true;
    try {
        if (checkIn.userLiked) {
            // 取消点赞
            await api.delete(`/checkins/${checkIn.id}/likes`);
            checkIn.userLiked = false;
            checkIn.likeCount = Math.max(0, checkIn.likeCount - 1);
            showNotify({ type: 'success', message: '已取消点赞' });
        } else {
            // 点赞
            await api.post(`/checkins/${checkIn.id}/likes`);
            checkIn.userLiked = true;
            checkIn.likeCount += 1;
            showNotify({ type: 'success', message: '点赞成功！' });
        }
    } catch (err) {
        showNotify({ type: 'danger', message: '操作失败，请稍后重试' });
    } finally {
        checkIn.likingLoading = false;
    }
};

// 显示评论对话框
const showCommentDialog = (checkIn) => {
    currentCheckInForComment.value = checkIn;
    newCommentText.value = '';
    showCommentDialogVisible.value = true;
};

// 添加评论
const handleAddComment = async () => {
    if (!newCommentText.value.trim()) {
        showNotify({ type: 'warning', message: '评论内容不能为空' });
        return;
    }
    
    commentLoading.value = true;
    try {
        const response = await api.post(`/checkins/${currentCheckInForComment.value.id}/comments`, {
            content: newCommentText.value
        });
        
        // 添加新评论到列表
        if (!currentCheckInForComment.value.comments) {
            currentCheckInForComment.value.comments = [];
        }
        currentCheckInForComment.value.comments.push(response.data);
        
        // 标记用户已评论
        currentCheckInForComment.value.userCommented = true;
        
        showNotify({ type: 'success', message: '评论成功！' });
        showCommentDialogVisible.value = false;
        newCommentText.value = '';
    } catch (err) {
        if (err.response && err.response.status === 400) {
            showNotify({ type: 'warning', message: '您已经评论过这条打卡记录了' });
        } else {
            showNotify({ type: 'danger', message: '评论失败，请稍后重试' });
        }
    } finally {
        commentLoading.value = false;
    }
};

// 处理文件上传
const afterRead = (file) => {
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    const maxSize = 5 * 1024 * 1024; // 5MB

    if (!allowedTypes.includes(file.file.type)) {
        showNotify({ type: 'warning', message: '只能上传 JPG, PNG, GIF, WEBP 格式的图片' });
        // 从fileList中移除无效文件
        const index = fileList.value.findIndex(f => f === file);
        if (index > -1) {
            fileList.value.splice(index, 1);
        }
        return;
    }

    if (file.file.size > maxSize) {
        showNotify({ type: 'warning', message: '图片大小不能超过 5MB' });
        // 从fileList中移除无效文件
        const index = fileList.value.findIndex(f => f === file);
        if (index > -1) {
            fileList.value.splice(index, 1);
        }
        return;
    }

    // 存储文件对象到数组
    uploadedFiles.value.push(file.file);
    file.status = 'done';
};

// 删除文件
const deleteFile = (file) => {
    // 从uploadedFiles数组中移除对应的文件
    const fileIndex = fileList.value.findIndex(f => f === file);
    if (fileIndex > -1 && fileIndex < uploadedFiles.value.length) {
        uploadedFiles.value.splice(fileIndex, 1);
    }
};

// 格式化时间戳
const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', { hour12: false });
};

// 预览图片
const previewImages = (imageUrlString, startIndex = 0) => {
  const imageUrls = getImageUrls(imageUrlString);
  const fullUrls = imageUrls.map(url => getImageUrl(url));
  
  // Vant 4.x 正确的调用方式，添加关闭按钮
  showImagePreview({
    images: fullUrls,
    startPosition: startIndex,
    closeable: true,
    closeIcon: 'cross',
    closeIconPosition: 'top-right'
  });
};

// 显示打卡详情（可以扩展为模态框）
const showCheckInDetail = (checkIn) => {
    // 这里可以添加更详细的打卡信息展示
    console.log('打卡详情:', checkIn);
};


onMounted(async () => {
  loading.value = true;
  await Promise.all([
    fetchTaskDetails(),
    fetchCheckIns()
  ]);
  loading.value = false;
});
</script>

<style scoped>
.task-detail-view {
  padding-bottom: 80px; /* 为悬浮按钮留出空间 */
}
.loading-container, .error-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.images-container {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.task-content {
  padding: 16px;
}
.check-in-button {
  position: fixed;
  right: 24px;
  bottom: 80px;
}
.check-in-list {
    margin-top: 16px;
}
.check-in-meta {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    font-size: 12px;
    color: #969799;
}

/* 新增样式 */
.check-in-card {
    margin-bottom: 16px;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.interaction-area {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background-color: #f8f9fa;
    border-top: 1px solid #eee;
}

.like-section, .comment-section {
    display: flex;
    align-items: center;
}

.comments-list {
    padding: 0 16px 12px;
    background-color: #f8f9fa;
}

.comment-item {
    padding: 8px 0;
    border-bottom: 1px solid #eee;
}

.comment-item:last-child {
    border-bottom: none;
}

.comment-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}

.comment-author {
    font-size: 12px;
    font-weight: bold;
    color: #323233;
}

.comment-time {
    font-size: 11px;
    color: #969799;
}

.comment-content {
    font-size: 14px;
    color: #646566;
    line-height: 1.4;
}

.comment-status {
    font-size: 11px;
    color: #969799;
    margin-left: 8px;
}
</style>