from django.contrib import admin

# 注意：本项目使用 Django REST Framework 提供 API 接口，
# 所有管理操作（用户管理、赛事管理、报名审核等）均通过 REST API 完成，
# 前端使用 Vue.js 管理后台，不需要 Django 原生 admin 站点。
# 因此此处未注册任何模型到 admin 后台。
