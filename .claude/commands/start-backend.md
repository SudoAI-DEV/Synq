---
alwaysApply: true
---


## 🚀 基础环境和工具

### Python 环境管理
- 所有运行 Python 相关的代码，都用 uv 执行
- Python 版本要求：3.11+
- 依赖管理：一律使用 uv



## 📋 需求管理流程

### 🤖 AI 自动需求评估
当接收到用户需求时，AI 需要首先进行自动评估：

#### 📊 需求复杂度评估标准

**🔥 大需求 (需要审阅) - 满足任何一条即为大需求：**
- 需要新增或修改后端 API 接口 (超过 2 个接口)
- 涉及新增页面或重构现有页面的主要功能
- 需要集成第三方服务或 AI 功能 (如 Agno 框架、DeepSeek、Gemini)
- 涉及认证系统变更 (Better Auth、飞书 OAuth)
- 预计开发时间超过 4 小时
- 涉及多个微服务的协调开发 (backend/frontend/jobs/raw2biz)
- 需要数据库迁移或模型重构
- 涉及元数据驱动 UI 系统的架构变更
- 需要新增或修改自举模式 (Bootstrap) 功能

**⚡ 小需求 (直接开发) - 以下类型直接开发：**
- 纯 UI 样式调整和 Tailwind CSS 优化
- 文案修改和国际化更新
- 简单的 Bug 修复
- 单个组件的功能增强
- 配置项调整
- 简单的数据展示格式调整
- 预计开发时间少于 2 小时

#### 🎯 AI 评估执行流程
1. **接收需求** → 自动分析需求复杂度
2. **大需求判定** → 自动生成需求文档模板并填充已知信息 (`features/YYYYMMDDHH_feature_name.md`)
3. **用户确认** → 等待用户审阅和修改需求文档
4. **开始开发** → 根据确认的需求文档执行开发
5. **模型同步** → 如果涉及模型变更，运行 `./scripts/model-version.sh` 同步
6. **API 接口同步** → 如果涉及后端 API 接口变动，启动后端后检查 `http://localhost:8000/docs`
7. **小需求判定** → 直接进入开发流程，无需文档

## 🏗️ 技术架构规范

### 前端技术栈 (Frontend)
- **框架**: Next.js 15.3.5 with App Router
- **语言**: TypeScript 5.7.2
- **样式**: Tailwind CSS 3.4.17
- **状态管理**: Zustand 或 React Built-in (useState, useEffect)
- **UI 组件**: 基于 Heroicons 和自定义组件
- **开发工具**: Turbopack (开发模式)
- **渲染方式**: 🔥 优先 SSR (服务端渲染) - 有利于 SEO 和首屏加载

### 后端技术栈 (Backend)
- **框架**: FastAPI 0.115.0
- **语言**: Python 3.11+
- **ORM**: SQLAlchemy 2.0.32 (异步模式)
- **数据库**: PostgreSQL (通过 asyncpg)
- **包管理**: uv (推荐) 或 pip
- **API 文档**: 自动生成 Swagger UI (`/docs`)

### 认证系统
- **双层架构**: Next.js (认证) + FastAPI (业务)
- **认证框架**: Better Auth 1.2.12
- **OAuth 集成**: 飞书 OAuth 2.0 登录
- **会话管理**: JWT Token 和会话持久化

### AI 服务
- **多智能体框架**: Agno (agno>=1.7.2)
- **搜索智能体**: 基于 DuckDuckGo 的信息搜索
- **提取智能体**: 使用 DeepSeek Chat 进行信息提取
- **验证智能体**: 使用 Gemini 进行信息验证

## 🎯 核心设计原则

### 自举模式优先 (Bootstrap Pattern)
1. **元数据驱动**: 所有 UI 功能基于模型元数据自动生成
2. **通用服务**: 使用 `UniversalCRUDService` 和 `UniversalMultiLevelCRUDService`
3. **零硬编码**: 避免在业务逻辑中硬编码特定模型名称
4. **配置优先**: 通过模型配置而非代码实现功能

### 组件设计规范
#### 元数据驱动组件
- **自举模式**: 基于后端模型元数据自动生成 CRUD 界面
- **通用表单**: 使用 `UniversalEntityForm` 组件
- **动态字段**: 通过 `FieldRendererRegistry` 注册自定义字段渲染器
- **多层级表单**: 支持关联数据的内联编辑

#### UI 组件规范
- **基础组件**: 位于 `src/components/ui/` 目录
- **业务组件**: 位于 `src/components/dashboard/` 和 `src/components/forms/`
- **布局组件**: 位于 `src/components/layout/`
- **响应式设计**: 使用 Tailwind CSS 断点

### API 设计规范

#### 自举模式 API
- **通用 CRUD**: 基于 `UniversalCRUDService` 自动生成
- **元数据 API**: 通过 `metadata_extractor` 提供模型元数据
- **多层级支持**: 使用 `UniversalMultiLevelCRUDService` 处理关联数据
- **约束验证**: 通过 `ConstraintValidator` 进行数据验证

#### API 端点规范
```
GET    /api/v1/metadata/{model}     - 获取模型元数据
GET    /api/v1/{model}/list         - 获取模型列表 (支持分页、搜索、排序)
POST   /api/v1/{model}/             - 创建模型实例
GET    /api/v1/{model}/{id}         - 获取模型详情
PUT    /api/v1/{model}/{id}         - 更新模型实例
DELETE /api/v1/{model}/{id}         - 删除模型实例

# 嵌套 API (关联数据管理)
GET    /api/v1/{parent_model}/{parent_id}/{child_model}/        - 获取关联数据列表
POST   /api/v1/{parent_model}/{parent_id}/{child_model}/        - 创建关联数据
GET    /api/v1/{parent_model}/{parent_id}/{child_model}/{id}    - 获取关联数据详情
PUT    /api/v1/{parent_model}/{parent_id}/{child_model}/{id}    - 更新关联数据
DELETE /api/v1/{parent_model}/{parent_id}/{child_model}/{id}    - 删除关联数据
```

#### 响应格式规范
- **成功响应**:
  ```json
  {
    "status": "success",
    "data": {}, // 或 []
    "message": "操作成功",
    "pagination": {} // 仅列表 API
  }
  ```
- **错误响应**:
  ```json
  {
    "detail": "错误信息",
    "status_code": 400
  }
  ```

### 数据模型管理
- **模型位置**: `models/dataengine_models/` 目录
- **元数据配置**: 在 `__table_args__` 和字段 `info` 中配置 UI 元数据
- **版本管理**: 使用 `./scripts/model-version.sh` 管理版本
- **数据库迁移**: 使用 Alembic 进行数据库迁移
- **脚本维护**: 永远不要用生成脚本来批量处理 model 的方式，会导致更多的问题

## 🔧 开发流程规范

### 代码质量
- **前端检查**: `npm run lint` (包含 TypeScript 检查)
- **后端检查**: `uv run black . && uv run ruff check .`
- **类型安全**: TypeScript 严格模式和 Python 类型注解
- **类型注解**: 使用 `Optional[T]` 而不是 `T | None` (兼容性考虑)

### 微服务协调
1. **模型同步**: 使用 `./scripts/model-version.sh` 管理模型版本
2. **服务独立**: 各微服务 (backend/frontend/jobs/raw2biz) 独立开发部署
3. **数据一致**: 共享模型库确保数据结构一致性
4. **API 契约**: 维护前后端 API 契约的稳定性

### API 开发流程
1. **先设计后开发**: 新增 API 必须先设计接口规范
2. **文档先行**: 在 `docs/api/` 目录创建详细的 API 文档
3. **类型安全**: 定义完整的 TypeScript 接口
4. **客户端封装**: 所有 API 调用必须在 `src/lib/api.ts` 中封装
5. **统一响应**: 遵循平台统一的响应格式规范
6. **自动验证**: 利用 Swagger UI 自动生成和验证 API 文档

### 性能要求
- **API 响应时间**: ≤ 200ms (99% 请求)
- **页面加载时间**: ≤ 3s (考虑数据复杂性)
- **Lighthouse Performance**: ≥ 85 分
- **Core Web Vitals**:
  - LCP (最大内容绘制): ≤ 2.5s
  - FID (首次输入延迟): ≤ 100ms
  - CLS (累积布局偏移): ≤ 0.1

### 安全规范
- **数据隔离**: 认证数据与业务数据分离 (admin schema)
- **权限控制**: 基于角色的访问控制 (计划中)
- **API 安全**: JWT 验证和请求速率限制
- **数据保护**: 敏感信息加密和安全传输

## 📁 项目结构
```
dataengine-kg-v2/
├── backend/           # FastAPI 后端服务
├── frontend/          # Next.js 前端应用
├── models/            # 共享数据模型
├── utils/             # 通用工具包
├── kgjob/             # 数据处理任务
├── raw2biz/           # 数据转换服务
├── features/          # 需求文档管理
├── docs/              # 项目文档
└── scripts/           # 管理脚本
```

## 🎯 质量保证原则
1. **设计验证**: 确保设计方案与平台架构一致
2. **集成测试**: 重点测试自举模式和多层级表单功能
3. **性能监控**: 关注元数据提取和动态 API 生成的性能
4. **用户体验**: 确保自动生成的界面用户友好
5. **API 一致性**: 确保前后端 API 接口的一致性和类型安全

## 🔄 部署和运维
- **环境配置**: 使用 Docker 和 docker-compose
- **数据库管理**: PostgreSQL with asyncpg
- **缓存策略**: 元数据缓存和 AI 响应缓存
- **监控日志**: 结构化日志和性能监控
- **错误处理**: 统一的错误处理和用户友好提示

---

遵循以上规范，确保 DataEngine Knowledge Graph Platform 的高质量、可维护性和用户体验。


cd backend &&  export $(grep -v '^#' .env | xargs) &&  uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload