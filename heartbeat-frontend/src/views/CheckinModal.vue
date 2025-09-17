<template>
  <van-popup v-model:show="show" round position="bottom" :style="{ height: '70%' }">
    <div class="modal-content">
      <van-nav-bar
        :title="'为 \'' + task.name + '\' 打卡'"
        left-text="取消"
        right-text="提交"
        @click-left="onClose"
        @click-right="onSubmit"
      />
      <van-form @submit="onSubmit">
        <van-cell-group inset>
          <van-field
            v-model="text"
            rows="3"
            autosize
            label="心情小记"
            type="textarea"
            maxlength="200"
            placeholder="记录下此刻的心情吧..."
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
              />
            </template>
          </van-field>
        </van-cell-group>
      </van-form>
    </div>
  </van-popup>
</template>

<script setup>
import { ref, watch } from 'vue'
import { showToast } from 'vant'
import apiClient from '@/api'

const props = defineProps({
  visible: {
    type: Boolean,
    required: true,
  },
  task: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['close', 'success'])

const show = ref(props.visible)
const text = ref('')
const fileList = ref([])
const uploadedFiles = ref([])

watch(() => props.visible, (newVal) => {
  show.value = newVal
  if (!newVal) {
    // Reset form when hiding
    text.value = ''
    fileList.value = []
    uploadedFiles.value = []
  }
})

const onClose = () => {
  emit('close')
}

const afterRead = (file) => {
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif'];
  const maxSize = 5 * 1024 * 1024; // 5MB

  if (!allowedTypes.includes(file.file.type)) {
    showToast('只能上传 JPG, PNG, GIF 格式的图片');
    // 从fileList中移除无效文件
    const index = fileList.value.findIndex(f => f === file);
    if (index > -1) {
      fileList.value.splice(index, 1);
    }
    return;
  }

  if (file.file.size > maxSize) {
    showToast('图片大小不能超过 5MB');
    // 从fileList中移除无效文件
    const index = fileList.value.findIndex(f => f === file);
    if (index > -1) {
      fileList.value.splice(index, 1);
    }
    return;
  }
  // 存储文件对象到数组
  uploadedFiles.value.push(file.file);
  file.status = 'done'
}

const deleteFile = (file) => {
  // 从uploadedFiles数组中移除对应的文件
  const fileIndex = fileList.value.findIndex(f => f === file);
  if (fileIndex > -1 && fileIndex < uploadedFiles.value.length) {
    uploadedFiles.value.splice(fileIndex, 1);
  }
}

const onSubmit = async () => {
  if (!props.task || !props.task.id) {
    showToast('无效的任务')
    return
  }

  const formData = new FormData()
  formData.append('task_id', props.task.id)
  formData.append('text', text.value)
  if (uploadedFiles.value.length > 0) {
    uploadedFiles.value.forEach((file) => {
      formData.append('images', file);
    });
  }

  try {
    await apiClient.post('/checkins/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    showToast('打卡成功！')
    emit('success')
    onClose()
  } catch (error) {
    console.error('Check-in failed:', error)
    showToast('打卡失败，请稍后再试')
  }
}
</script>

<style scoped>
.modal-content {
  padding-top: 46px; /* Height of the nav-bar */
}
</style>