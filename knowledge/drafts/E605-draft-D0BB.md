# E605 — meson i18n.merge_file 位置参数被新版 meson 拒绝

## 错误特征
```
meson.build:1:0: ERROR: Function does not take positional arguments.
```
触发于 `i18n.merge_file('com.endlessm.ParentalControls.policy', input: ..., output: ...)` 这类旧式位置参数写法。

## 触发条件
- 构建系统: meson（≥1.12）
- 阶段: configuration（meson setup）
- 上游 meson.build 用 `i18n.merge_file('out.policy', input:, output: ...)` 形式传入 output 位置参数

## 根因分析
上游老项目（如 libmalcontent 0.10.2）用位置参数形式把 output 文件名作为 merge_file 的第一参数；新版 meson（1.12 实测）的函数签名不再接受位置参数，必须用关键字形式，配置阶段直接 `ERROR: Function does not take positional arguments` 中止。

## 解决方案

### 推荐方案
patch meson.build，把
```meson
i18n.merge_file('com.endlessm.ParentalControls.policy',
  input: '...in', output: '...', po_dir: po_dir, ...)
```
改为纯关键字形式（删除位置参数，output 关键字保留同名文件值）：
```meson
i18n.merge_file(
  input: '...in', output: '...', po_dir: po_dir, ...)
```

### 禁止做法
- ❌ 不加 patch 硬跑新版 meson（配置必然失败）
- ❌ 用 `--` 或环境标志绕过（无此机制，须改 build 文件）

## 验证
```bash
meson setup builddir          # 修复前: ERROR: Function does not take positional arguments
# 应用 0001 patch 后
meson setup builddir          # 通过，生成 com.endlessm.ParentalControls.policy
```

## 适用与不适用边界
- 适用：所有 glib/meson 系旧项目用 i18n.merge_file 位置参数适配新版 meson 工具链
- 不适用：meson <1.12（位置参数仍合法）；无 i18n.merge_file 调用的项目

## 关联条目
- 相关（同项目 meson 兼容族）: E606（gdbus-codegen wrapper）、E609（subproject 预置）