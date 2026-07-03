# 库房备件管理系统

基于 Python + Django 的库房备件管理系统，支持多组别并行管理，实现库存信息透明化与操作权限隔离。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.x + Django 4.2 |
| 前端 | Django Templates + Airbnb 风格设计系统 |
| 数据库 | SQLite（可切换 PostgreSQL / MySQL） |
| 权限 | Django Group + 自定义 Middleware + Decorator |

## 快速开始

```bash
cd D:\code\kufang

# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库
python manage.py makemigrations
python manage.py migrate

# 3. 创建演示数据
python manage.py seed_data

# 4. 启动服务
python manage.py runserver
```

浏览器访问 **http://127.0.0.1:8000**

## 演示账号

所有用户密码均为 `demo123`：

| 用户名 | 组别 | 角色 |
|---|---|---|
| `zhangsan` | 主机组 (A) | 操作员 |
| `lisi` | 主机组 (A) | 操作员 |
| `wangwu` | 冷却组 (B) | 操作员 |
| `zhaoliu` | 冷却组 (B) | 操作员 |
| `sunqi` | 电力组 (C) | 操作员 |
| `zhouba` | 电力组 (C) | 操作员 |
| `admin` | — | 超级管理员 |

## 项目结构

```
kufang/
├── manage.py
├── requirements.txt
├── config/                        # Django 项目配置
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/                  # 用户 & 组管理
│   │   ├── models.py              # UserProfile (扩展 User, 绑定 Group)
│   │   ├── views.py               # 登录/登出
│   │   └── urls.py
│   └── warehouse/                 # 核心业务
│       ├── models.py              # Inventory, InboundRecord, OutboundRecord, AuditLog
│       ├── views.py               # 仪表盘 / 库存CRUD / 入库 / 出库 / 流水 / 导出
│       ├── urls.py
│       ├── admin.py
│       ├── middleware.py          # UserGroupMiddleware
│       ├── decorators.py          # @require_group_owner
│       ├── context_processors.py  # user_group 模板变量
│       └── management/commands/
│           └── seed_data.py       # 演示数据生成
├── templates/                     # Django 模板
│   ├── base.html                  # 全局布局 (侧边栏 + Toast)
│   ├── login.html                 # 登录页 (快速登录面板)
│   ├── dashboard.html             # 仪表盘
│   ├── inventory_list.html        # 库存列表
│   ├── inventory_detail.html      # 备件详情
│   ├── inventory_edit.html        # 编辑备件
│   ├── inbound.html               # 入库登记
│   ├── outbound.html              # 出库登记
│   └── log.html                   # 出入库流水
└── static/
    └── css/
        └── app.css                # Airbnb 风格样式 (DESIGN.md)
```

## 功能模块

### 仪表盘
- 本组库存总数、备件种类
- 本月入库 / 出库次数统计
- 低库存预警 Top 5（高亮缺货项）
- 全局动态流水（最近 10 条，脱敏）

### 库存列表
- 关键字搜索（备件名称、编码、规格型号）
- 组别筛选 + 库存状态筛选（正常 / 预警 / 缺货）
- 分页展示（默认 20 条 / 页）
- 权限按钮：
  - **本组数据** → `[入库] [出库] [编辑]`
  - **其他组数据** → `[查看详情]`
- CSV 导出

### 入库登记
- 选择已有备件 或 新建备件
- 入库类型：采购入库 / 归还入库 / 盘盈
- 新建备件额外字段：编码、名称、规格、单位、安全库存、位置、使用状态、质量等级、生产厂家、配置、重要程度、涉密等级、品种标识码
- 自动继承操作员组别，生成流水日志

### 出库登记
- 仅显示本组有库存的备件
- 前端校验数量 ≤ 当前库存
- 后端 `select_for_update()` 原子更新防并发超卖
- 严格 group_id 校验，扣减后 < 0 回滚报错

### 出入库流水
- 按操作时间、组别、操作类型筛选
- 字段：时间、操作人、组别、备件名称、变动数量、变动前后库存、备注

## 权限设计

```
┌─────────────┬──────────┬──────────┐
│ 功能模块      │ 本组数据   │ 其他组数据 │
├─────────────┼──────────┼──────────┤
│ 库存列表查看  │ 可操作    │ 仅查看    │
│ 入库登记      │ 允许      │ 禁止      │
│ 出库登记      │ 允许      │ 禁止      │
│ 库存详情      │ 完整信息  │ 基础信息   │
│ 系统设置      │ 禁止      │ 禁止      │
└─────────────┴──────────┴──────────┘
```

### 数据隔离策略
- 所有业务表包含 `group` 外键
- `UserGroupMiddleware` 将用户组注入 `request.user_group`
- `@require_group_owner` 装饰器校验写操作归属，不匹配返回 403
- 列表接口通过模板中 `item.group == user_group` 控制按钮显隐

## 数据模型

### Inventory（备件库存）
| 字段 | 类型 | 说明 |
|---|---|---|
| code | CharField (unique) | 备件编码 |
| name | CharField | 名称 |
| spec | CharField | 规格型号 |
| quantity | IntegerField | 当前数量 |
| unit | CharField | 单位 |
| safety_stock | IntegerField | 安全库存阈值 |
| location | CharField | 存放位置 |
| group | FK(Group) | 所属组 |
| status | CharField | 使用状态 |
| quality | CharField | 质量等级 |
| manufacturer | CharField | 生产厂家 |
| configuration | TextField | 配置 |
| importance | CharField | 重要程度 |
| security_level | CharField | 涉密等级 |
| variety_code | CharField | 品种标识码 |

### AuditLog（出入库流水）
| 字段 | 类型 | 说明 |
|---|---|---|
| inventory | FK(Inventory) | 备件 |
| operator | FK(User) | 操作人 |
| group | FK(Group) | 所属组 |
| change_type | CharField | 入库/出库 |
| delta | IntegerField | 变动数量 |
| before_qty | IntegerField | 变动前库存 |
| after_qty | IntegerField | 变动后库存 |
| note | TextField | 备注 |

## 设计系统

采用 Airbnb 风格设计规范（见 `DESIGN.md`）：

- **主色** `#FF385C`（珊瑚红 / Rausch）— 仅用于 CTA 按钮和关键数据
- **圆角系统** — 全圆角：按钮 8px、卡片 14px、搜索栏/胶囊 9999px
- **阴影** — 极致克制，主要靠 1px hairline 描边区分层级
- **字体** — Segoe UI / system-ui，字重 400-700
- **画布** — 纯白 `#FFFFFF`，无暗色模式
