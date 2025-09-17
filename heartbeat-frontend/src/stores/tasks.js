import { defineStore } from 'pinia';
import api from '@/api';

export const useTaskStore = defineStore('tasks', {
  state: () => ({
    tasks: [],
  }),
  actions: {
    async fetchTasks() {
      try {
        const response = await api.get('/tasks/');
        this.tasks = response.data;
      } catch (error) {
        console.error('Failed to fetch tasks:', error);
        // 在这里可以添加错误处理逻辑，例如显示一个提示
      }
    },
    async createTask(taskData) {
      try {
        const response = await api.post('/tasks/', taskData);
        this.tasks.push(response.data);
      } catch (error) {
        console.error('Failed to create task:', error);
        throw error; // 抛出错误，以便组件可以捕获它
      }
    },
    async updateTask(taskId, taskUpdate) {
      try {
        const response = await api.put(`/tasks/${taskId}`, taskUpdate);
        const index = this.tasks.findIndex(t => t.id === taskId);
        if (index !== -1) {
          this.tasks[index] = response.data;
        }
      } catch (error) {
        console.error('Failed to update task:', error);
        throw error;
      }
    },
  },
});