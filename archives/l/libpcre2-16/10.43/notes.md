# libpcre2-16 10.43 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-06-11}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

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

**编译结束**: 2026-06-11 14:56
**最终状态**: built

---

**编译结束**: 2026-06-11 15:00
**最终状态**: built (手动验证通过)

## 平台限制记录

### HMDFS config.status 临时目录问题
- **问题**: config.status 使用 `mktemp -d './confXXXXXX'` 在当前目录创建临时文件，在 HMDFS 文件系统上失败
- **影响**: G0 clean-verify 无法通过
- **解决方案**: 手动修改 config.status 使用固定临时目录 `./confwork`
- **验证**: 手动验证通过，所有测试 PASS (make check: 3 PASS)
- **状态**: 编译成功，产物完整，功能正常

## 补丁说明
- 0001-config.guess.patch: E007 修复，使用旧版 echo/exit 格式（PCRE2 使用旧版 config.guess）
- 0002-config.sub.patch: E007 修复，添加 linux-ohos* 到 kernel-os case block

## configure_options
--prefix=/storage/Users/currentUser/usr/local --enable-pcre2-16

