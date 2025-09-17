import axios from 'axios';

const API_URL = 'http://localhost:8000'; // 您的 FastAPI 后端地址

export const login = (username, password) => {
  const params = new URLSearchParams();
  params.append('username', username);
  params.append('password', password);
  return axios.post(`${API_URL}/auth/token`, params);
};

export const register = (username, password) => {
  return axios.post(`${API_URL}/auth/register`, {
    username,
    password,
  });
};

export const refreshToken = (token) => {
  return axios.post(`${API_URL}/auth/refresh`, null, { // `null` as we pass the token in the query
    params: { refresh_token: token }
  });
};