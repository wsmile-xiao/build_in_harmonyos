# munit 0.4.1 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-08-31}
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

## 编译过程

### 1. 源码修改

**问题**: `tmpfile()` 在某些 POSIX 系统（如 OHOS）上失败，因为 `/tmp` 可能是只读文件系统。

**解决方案**: 修改 `munit.c` 第 1331 行，使用更可移植的 POSIX 方案：
- 使用 `mkstemp()` 在 `$TMPDIR`（回退到 `/tmp`）创建临时文件
- 立即 `unlink()` 确保文件在进程退出时自动删除
- 用 `fdopen()` 转换为 FILE* 供 munit 使用
- **符合项目规则 R8**：不使用平台宏，所有 POSIX 系统统一实现

```c
/* Use TMPDIR for temporary files - more portable than tmpfile() */
{
  const char* tmpdir = getenv("TMPDIR");
  if (tmpdir == NULL) tmpdir = "/tmp";
  char tmppath[PATH_MAX];
  snprintf(tmppath, sizeof(tmppath), "%s/munit_stderr_XXXXXX", tmpdir);
  int tmpfd = mkstemp(tmppath);
  if (tmpfd != -1) {
    unlink(tmppath);
    stderr_buf = fdopen(tmpfd, "w+");
    if (stderr_buf == NULL) close(tmpfd);
  }
}
```

### 2. 编译命令

```bash
make CC=clang CFLAGS="-std=c99 -fPIC -D__OHOS__" example
```

### 3. 测试结果

所有 11 个测试用例全部通过（包括参数化测试）：
- /example/compare: OK
- /example/rand: OK
- /example/parameters (9 种组合): 全部 OK

### 4. 构建系统

munit 支持两种构建方式：
- **Makefile**: 简单的示例构建（仅编译 example）
- **Meson**: 完整的库构建和安装

由于没有 autotools 配置，将使用 Meson 构建系统创建 Conan 配方。
---

**编译结束**: 2026-08-31 20:19
**最终状态**: built
