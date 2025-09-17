<template>
  <div v-if="visible" class="modal-overlay">
    <div class="modal-content">
      <span class="close-btn" @click="close">&times;</span>
      <h2>打卡详情</h2>
      <div v-if="checkin">
        <p><strong>打卡人:</strong> {{ isMyCheckin ? '我的打卡' : 'Ta的打卡' }}</p>
        <p><strong>打卡时间:</strong> {{ new Date(checkin.created_at).toLocaleString() }}</p>
        <p><strong>心情文字:</strong> {{ checkin.message }}</p>
        <div v-if="checkin.image_url">
          <strong>打卡图片:</strong>
          <div class="images-container">
            <img 
              v-for="(imageUrl, index) in getImageUrls(checkin.image_url)" 
              :key="index"
              :src="getImageUrl(imageUrl)" 
              alt="Check-in Image" 
              class="checkin-image" 
              @click="previewImages(checkin.image_url, index)"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { showImagePreview } from 'vant'

const props = defineProps({
  visible: {
    type: Boolean,
    required: true
  },
  checkin: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])

const authStore = useAuthStore()

const isMyCheckin = computed(() => {
  if (!props.checkin || !authStore.user) {
    return false
  }
  return props.checkin.user_id === authStore.user.id
})

const getImageUrl = (path) => {
  // Assuming the backend serves static files from the root
  return path;
}

// 解析多个图片URL
const getImageUrls = (imageUrlString) => {
  if (!imageUrlString) return [];
  return imageUrlString.split(',').filter(url => url.trim());
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

const close = () => {
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  position: relative;
}

.close-btn {
  position: absolute;
  top: 10px;
  right: 15px;
  font-size: 24px;
  cursor: pointer;
}

.images-container {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.checkin-image {
  max-width: 150px;
  height: auto;
  margin-top: 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: transform 0.2s;
}

.checkin-image:hover {
  transform: scale(1.05);
}
</style>