# unixcw 3.5.1 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-09-13}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

| 补丁文件 | 修改内容 | 说明 |
|----------|----------|------|
| `patches/0001-src-cwutils-i18n.c.patch` | `src/cwutils/i18n.c`：将 `i18n_gettext` 函数体整体替换为单一 `return msgid;`（保留 `{ }` 结构） | OHOS 无可用 libintl，`_()` 宏走 `i18n_gettext` 时稳定返回原串。2026-09-13 检视修复：原补丁误删整个函数体导致空体 `{}`，`_()` 调用触发 UB（-Werror=return-type 下编译失败）。重写后已在 conandata.yml `patches:` 中声明（原 `patches: {}` 导致补丁不会被 `apply_conandata_patches` 应用）。本地 conan create + test_package 1/1 验证通过。 |

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}
---

**编译结束**: 2026-09-13 09:36
**最终状态**: built
