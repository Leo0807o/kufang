---
version: alpha
name: Airbnb
description: 温暖、慷慨的消费者旅行市场 — 珊瑚红主调、摄影驱动、全圆角 UI，建立在纯白画布和 Airbnb Rausch 之上。
colors:
  primary: "#ff385c"
  primary-active: "#e00b41"
  primary-disabled: "#ffd1da"
  primary-error-text: "#c13515"
  primary-error-text-hover: "#b32505"
  luxe: "#460479"
  plus: "#92174d"
  ink: "#222222"
  body: "#3f3f3f"
  muted: "#6a6a6a"
  muted-soft: "#929292"
  hairline: "#dddddd"
  hairline-soft: "#ebebeb"
  border-strong: "#c1c1c1"
  canvas: "#ffffff"
  surface-soft: "#f7f7f7"
  surface-card: "#ffffff"
  surface-strong: "#f2f2f2"
  on-primary: "#ffffff"
  on-dark: "#ffffff"
  legal-link: "#428bff"
  star-rating: "#222222"
  scrim: "#000000"
typography:
  rating-display:
    fontFamily: Airbnb Cereal VF
    fontSize: 64px
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: -1px
  display-xl:
    fontFamily: Airbnb Cereal VF
    fontSize: 28px
    fontWeight: 700
    lineHeight: 1.43
    letterSpacing: 0
  display-lg:
    fontFamily: Airbnb Cereal VF
    fontSize: 22px
    fontWeight: 500
    lineHeight: 1.18
    letterSpacing: -0.44px
  display-md:
    fontFamily: Airbnb Cereal VF
    fontSize: 21px
    fontWeight: 700
    lineHeight: 1.43
    letterSpacing: 0
  display-sm:
    fontFamily: Airbnb Cereal VF
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.20
    letterSpacing: -0.18px
  title-md:
    fontFamily: Airbnb Cereal VF
    fontSize: 16px
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: 0
  title-sm:
    fontFamily: Airbnb Cereal VF
    fontSize: 16px
    fontWeight: 500
    lineHeight: 1.25
    letterSpacing: 0
  body-md:
    fontFamily: Airbnb Cereal VF
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0
  body-sm:
    fontFamily: Airbnb Cereal VF
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.43
    letterSpacing: 0
  caption:
    fontFamily: Airbnb Cereal VF
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.29
    letterSpacing: 0
  caption-sm:
    fontFamily: Airbnb Cereal VF
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.23
    letterSpacing: 0
  badge:
    fontFamily: Airbnb Cereal VF
    fontSize: 11px
    fontWeight: 600
    lineHeight: 1.18
    letterSpacing: 0
  micro-label:
    fontFamily: Airbnb Cereal VF
    fontSize: 12px
    fontWeight: 700
    lineHeight: 1.33
    letterSpacing: 0
  uppercase-tag:
    fontFamily: Airbnb Cereal VF
    fontSize: 8px
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: 0.32px
  button-md:
    fontFamily: Airbnb Cereal VF
    fontSize: 16px
    fontWeight: 500
    lineHeight: 1.25
    letterSpacing: 0
  button-sm:
    fontFamily: Airbnb Cereal VF
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.29
    letterSpacing: 0
  link:
    fontFamily: Airbnb Cereal VF
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.43
    letterSpacing: 0
  nav-link:
    fontFamily: Airbnb Cereal VF
    fontSize: 16px
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: 0
rounded:
  none: 0px
  xs: 4px
  sm: 8px
  md: 14px
  lg: 20px
  xl: 32px
  full: 9999px
spacing:
  xxs: 2px
  xs: 4px
  sm: 8px
  md: 12px
  base: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  section: 64px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-md}"
    rounded: "{rounded.sm}"
    padding: 14px 24px
    height: 48px
  button-primary-active:
    backgroundColor: "{colors.primary-active}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.sm}"
  button-primary-disabled:
    backgroundColor: "{colors.primary-disabled}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.sm}"
  button-secondary:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.button-md}"
    rounded: "{rounded.sm}"
    padding: 13px 23px
    height: 48px
  button-tertiary-text:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.button-md}"
  button-pill-rausch:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-sm}"
    rounded: "{rounded.full}"
    padding: 10px 20px
  search-orb:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.full}"
    height: 48px
  search-bar-pill:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.full}"
    padding: 14px 24px
    height: 64px
  search-field-segment:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.caption}"
    padding: 8px 24px
  icon-button-circle:
    backgroundColor: "{colors.surface-strong}"
    textColor: "{colors.ink}"
    rounded: "{rounded.full}"
    height: 32px
  icon-button-outline:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.full}"
    height: 40px
  top-nav:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.nav-link}"
    height: 80px
  product-tab-active:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.nav-link}"
    rounded: "{rounded.none}"
  product-tab-inactive:
    backgroundColor: transparent
    textColor: "{colors.muted}"
    typography: "{typography.nav-link}"
  category-strip:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.muted}"
    typography: "{typography.button-sm}"
  category-tab-active:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.button-sm}"
    rounded: "{rounded.none}"
  property-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
  property-card-photo:
    rounded: "{rounded.md}"
  experience-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.title-md}"
    rounded: "{rounded.md}"
  city-link-block:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.title-sm}"
  rating-display-card:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.rating-display}"
  guest-favorite-badge:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.badge}"
    rounded: "{rounded.full}"
    padding: 4px 10px
  new-tag:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.uppercase-tag}"
    rounded: "{rounded.full}"
    padding: 2px 6px
  amenity-row:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    padding: 12px 0
  reviews-card:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
  host-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: 24px
  reservation-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: 24px
  date-picker-day:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.full}"
  date-picker-day-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.on-dark}"
    rounded: "{rounded.full}"
  text-input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.sm}"
    padding: 14px 12px
    height: 56px
  footer-light:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    padding: 48px 80px
  footer-link:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
  legal-band:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.muted}"
    typography: "{typography.caption-sm}"
---

## Overview

Airbnb 的设计语言建立在一个核心张力之上：**温暖 vs 克制**。

品牌色 Rausch（`#FF385C`）是一个饱满但不过分热烈、不轻浮的珊瑚红 — 它承载了页面上几乎所有交互信号：主按钮、搜索球、心形收藏、分类指示器。页面其余部分退到纯白画布（无暗色模式），让房源摄影和文字信息占据绝对主导。

字重策略刻意偏轻 — 标题在 22-28px 区间，字重仅 500-700 — 不靠沉重的字体来制造视觉层级，而是靠留白、灰度和比例。

## Colors

- **primary `#FF385C`** — Rausch，唯一品牌强调色。所有 CTA、搜索激活态、心形收藏、分类激活指示。
- **ink `#222222`** — 主文字，从不用纯黑 `#000`，比 #333 更暖。
- **body `#3F3F3F`** — 长文本正文，比 ink 浅以减轻疲劳。
- **muted `#6A6A6A`** — 次级信息、日期范围、元数据。
- **muted-soft `#929292`** — 禁用链接、最低优先级信息。
- **hairline `#DDDDDD`** — 默认 1px 分割线。
- **hairline-soft `#EBEBEB`** — 轻分割线、卡片内部边界。
- **canvas `#FFFFFF`** — 纯白页面底色，无暗色模式。
- **surface-soft `#F7F7F7`** — 最轻填充面。
- **surface-strong `#F2F2F2`** — 图标按钮默认背景。
- **star-rating `#222222`** — 星级评分刻意不用金色，避免廉价感。
- **legal-link `#428BFF`** — 法律条款链接蓝，仅用于 Footer 合规区。
- **scrim `#000000`** — 模态框遮罩，50% 透明度。

子品牌色：**luxe `#460479`**（紫色）、**plus `#92174D`**（品红）。

## Typography

字体族：`Airbnb Cereal VF`（可变字体）→ `Circular` → `-apple-system, system-ui, Roboto, Helvetica Neue, sans-serif`。

层级设计：
- **rating-display** 64px/700/-1px — 房源详情大评分数字 "4.81"。
- **display-xl** 28px/700 — 首页主标题。
- **display-lg** 22px/500/-0.44px — 房源卡片标题，字重仅 500（Airbnb 独特做法）。
- **display-md / sm** 21px/700、20px/600 — 详情区块标题、子标题。
- **title-md / sm** 16px/600、16px/500 — 城市链接、Footer 列标题。
- **body-md / sm** 16px/400/1.5、14px/400/1.43 — 正文、卡片元信息。
- **caption / caption-sm** 14px/500、13px/400 — 搜索栏标签、Footer 版权。
- **badge** 11px/600 — "Guest favorite" 标签。
- **micro-label** 12px/700 — 设施标签。
- **uppercase-tag** 8px/700/0.32px — 全大写标签（"NEW"）。
- **button-md / sm** 16px/500、14px/500 — 按钮字体。
- **nav-link** 16px/600 — 顶部导航。

## Layout

页面最大宽度无硬性限制，但房源卡片网格、搜索栏和 Footer 使用统一的 24px/80px 水平内边距。纵向间距以 `section: 64px` 为区块单位。

## Elevation & Depth

Airbnb 的阴影语言极其克制。全局仅一种阴影：`0 0 0 1px rgba(0,0,0,0.02), 0 2px 6px rgba(0,0,0,0.04), 0 4px 8px rgba(0,0,0,0.1)` — 几乎不可见，仅给出最微弱的层级暗示。卡片和搜索栏靠 1px hairline 描边而非阴影来区分。

## Shapes

全圆角系统 — 没有任何硬角交互元素：
- **按钮** — 8px 圆角（pill 变体用 9999px）
- **卡片** — 14px 圆角（房源卡片、体验卡片、照片本身）
- **搜索栏** — 9999px 全圆角胶囊
- **分类条** — 32px 圆角
- **图标按钮、日期选择器** — 9999px 正圆形
- **文本输入框** — 8px

## Components

Airbnb 的组件系统高度细化，覆盖了从导航到表单到日期的完整交互：

**导航层**：`top-nav` 80px 高度白底，`product-tab-active/inactive` 通过 `ink` vs `muted` 颜色区分选中态（不用下划线指示器）。

**搜索**：`search-bar-pill` 64px 高，纯白底的全圆角胶囊，内部 `search-field-segment` 透明底分段。搜索按钮 `search-orb` 48px 正圆，珊瑚红实心。

**卡片**：`property-card` / `experience-card` 14px 圆角，白底无阴影，靠 1px hairline 描边。`property-card-photo` 独立圆角定义。

**按钮**：三级 — `button-primary`（珊瑚实心）、`button-secondary`（白底黑字带描边）、`button-tertiary-text`（纯文字无背景）。另有 `button-pill-rausch` 胶囊变体。

**数据输入**：`text-input` 56px 高、8px 圆角。`date-picker-day` 和 `date-picker-day-selected`（ink 实心反色）组成完整的日期选择器。

**评价与徽章**：`rating-display-card` 64px 大字评分，`guest-favorite-badge` 全圆角白底标签。

## Do's and Don'ts

- ✅ 只用 Rausch 一种颜色做所有交互信号 — 克制是核心。
- ✅ 字重偏轻，靠留白和灰度而非粗体制造层级。
- ✅ 全圆角 — 按钮、卡片、搜索栏、标签，无一例外。
- ✅ 星级评分用 `#222` 不用金色 — 避免廉价感。
- ✅ 阴影极淡甚至不用 — 靠 1px hairline 描边区分层级。
- ❌ 不要在 Airbnb 上使用暗色模式 — 画布永远是纯白。
- ❌ 不要引入第二种强调色 — 子品牌 luxe/plus 仅在对应产品区使用。
- ❌ 不要用硬角（0px border-radius）做任何交互元素。
