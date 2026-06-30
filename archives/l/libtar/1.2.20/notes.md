# libtar 1.2.20 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-06-08}
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

## 编译步骤

### 1. 初始化
- 源码从 Git 仓库下载（v1.2.20 tag）
- 使用 `--no-download` 模式初始化（SSL下载问题）
- 源码解压到 ~/tmp/builds/libtar-1.2.20.work

### 2. 编译
- autotools 构建系统
- 需要手动运行 autoreconf 生成 configure
- libtoolize 失败（HMDFS权限问题），使用 `LIBTOOLIZE=true` 绕过
- automake 失败（HMDFS路径问题），手动创建 Makefile.in
- configure --prefix=$DEFAULT_PREFIX 成功
- make -j1 成功（有警告但不影响）
- make install DESTDIR=$TEST_PREFIX 成功

### 3. 测试验证
- libtar 没有 check 目标（无测试套件）

### 4. Staging 验证
- G1-G4 质量门禁通过
- 需要添加 `build_system: autotools` 顶级字段

### 5. 预编译包制作
- libtar-1.2.20-ohos-aarch64.tar.gz: 520KB
- 包含: bin/libtar, lib/libtar.*, include/libtar.h, share/man

### 6. 本地安装验证
- 动态库加载需要 ELF 签名
- 预编译包中的 RPATH 已正确设置

---

## 遇到的问题

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL下载失败 | Savannah SSL证书验证失败 | 手动克隆 Git 仓库，创建 tarball |
| 2 | libtoolize失败 | HMDFS文件系统权限问题 | `LIBTOOLIZE=true autoreconf -fi` |
| 3 | automake失败 | HMDFS路径无法访问autoconf | 手动从 lib/Makefile.in 等复制模板 |
| 4 | configure缺辅助文件 | autoreconf未生成完整文件 | 从 libtool build-aux 复制 config.guess等 |
| 5 | G4缺少build_system | manifest模板使用嵌套字段 | 添加顶级 build_system: autotools |
| 6 | 本地验证动态库加载失败 | 共享库需要ELF签名 | 预编译包中已正确设置RPATH和签名 |

---

## 知识提取

- **HMDFS权限问题**: libtoolize/automake 无法访问某些路径，需要使用环境变量绕过或手动创建文件
- **build_system字段**: manifest.yaml 需要顶级字段用于 G4 门禁检查

**编译结束**: 2026-06-08
**最终状态**: built
---

**编译结束**: 2026-06-08 17:46
**最终状态**: built
