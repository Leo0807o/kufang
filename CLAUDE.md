## Design System

本项目使用 DESIGN.md 作为唯一的视觉真相源。**在生成或修改任何 UI 代码之前，你必须：**

1. **先读** `DESIGN.md` — 获取完整的设计 Token（颜色、字体、间距、圆角、阴影）和设计理念
2. **只使用** DESIGN.md 中定义的 Token 值，不要凭空捏造颜色或字号
3. **遵守** Do's and Don'ts 中的约束规则

### 硬规则

- 颜色：通过语义名称引用（`primary` / `accent` / `surface` / `card` / `text-primary` / `text-secondary` / `border` / `success`），禁止直接硬编码 hex
- 字体：`Segoe UI, system-ui, -apple-system, sans-serif`，字重层级 700 → 600 → 500 → 400
- 圆角：按钮用 `9999px`（胶囊形），卡片用 `10px`，图标容器用 `6px`
- 间距：4px 基准网格 — `xs(4) → sm(8) → md(16) → lg(24) → xl(32) → 2xl(48) → 3xl(64)`
- 阴影：卡片 `0 1px 3px` hover 升至 `0 4px 16px`，按钮带珊瑚色投影
- 强调色 `#E8734A` 只能用于 CTA 按钮和关键数据，禁止做大面积背景或装饰

### 每次 UI 变更后

```bash
npx @google/design.md lint DESIGN.md
```

确保 Token 未被破坏。新增页面时，将新页面用到的语义颜色回填到 DESIGN.md 的 `components` 字段中。
