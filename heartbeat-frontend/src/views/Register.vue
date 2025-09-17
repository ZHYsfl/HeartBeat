<template>
  <div class="register-container">
    <div class="register-box">
      <div class="title">HeartBeat</div>
      <div class="subtitle">创建您的新账户</div>
      <form @submit.prevent="handleRegister">
        <div class="input-group">
          <input type="text" v-model="username" placeholder="用户名" required />
        </div>
        <div class="input-group">
          <input type="password" v-model="password" placeholder="密码" required />
        </div>
        <div class="input-group">
          <input type="password" v-model="confirmPassword" placeholder="确认密码" required />
        </div>
        <div v-if="error" class="error-message">{{ error }}</div>
        <button type="submit" class="register-btn">注册</button>
      </form>
      <div class="login-link">
        已有账户？ <router-link to="/login">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { register } from '@/api/auth';

const username = ref('');
const password = ref('');
const confirmPassword = ref('');
const error = ref('');
const router = useRouter();

const handleRegister = async () => {
  if (password.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致';
    return;
  }
  error.value = '';
  try {
    await register(username.value, password.value);
    // 注册成功后，可以自动跳转到登录页或直接登录
    router.push('/login');
  } catch (err) {
    error.value = err.response?.data?.detail || '注册失败，请稍后再试';
  }
};
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #fce4ec; /* A light pink background */
}

.register-box {
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
  text-align: center;
}

.title {
  font-size: 2.5rem;
  font-weight: bold;
  color: #e91e63; /* Hot pink */
  margin-bottom: 10px;
}

.subtitle {
  font-size: 1rem;
  color: #888;
  margin-bottom: 30px;
}

.input-group {
  margin-bottom: 20px;
}

.input-group input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-sizing: border-box;
}

.error-message {
  color: #f44336;
  margin-bottom: 15px;
}

.register-btn {
  width: 100%;
  padding: 12px;
  background-color: #e91e63;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s;
}

.register-btn:hover {
  background-color: #c2185b;
}

.login-link {
  margin-top: 20px;
  font-size: 0.9rem;
}

.login-link a {
  color: #e91e63;
  text-decoration: none;
}
</style>