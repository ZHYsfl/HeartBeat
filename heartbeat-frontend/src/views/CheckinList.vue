<template>
  <van-cell-group inset>
    <van-cell
      v-for="task in tasks"
      :key="task.id"
      :title="task.name"
      :class="{ 'completed-task': task.checked }"
      :is-link="task.checked"
      @click="onTaskItemClick(task)"
    >
      <template #value>
        <van-button
          v-if="!task.checked"
          size="small"
          type="primary"
          @click.stop="onCheckinButtonClick(task)"
        >
          去打卡
        </van-button>
        <span v-else>已完成</span>
      </template>
    </van-cell>
  </van-cell-group>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

defineProps({
  tasks: {
    type: Array,
    required: true,
  },
});

const emit = defineEmits(['task-click', 'view-detail'])

const onCheckinButtonClick = (task) => {
  emit('task-click', task)
}

const onTaskItemClick = (task) => {
  if (task.checked) {
    emit('view-detail', task.last_checkin)
  }
}
</script>

<style scoped>
.completed-task .van-cell__title {
  text-decoration: line-through;
  color: #969799;
}
.completed-task {
  cursor: pointer;
}
</style>