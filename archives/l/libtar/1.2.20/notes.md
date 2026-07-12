# libtar 1.2.20 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### 1. 初始化
- 源码从 Git 仓库下载（v1.2.20 tag）
- 使用 `--no-download` 模式初始化（SSL下载问题）
- 源码解压到 ~/tmp/builds/libtar-1.2.20.work

### 2. 编译
- autotools 构建系统
- 源码为 git snapshot，无预生成 configure
- **CI 修复**: CI worker 仅有 `autoconf`/`autoreconf`（`/data/service/hnp/bin/`），缺少 `automake`/`libtoolize`
- 方案: 预生成全部 autotools 文件（configure, config.h.in, Makefile.in, ltmain.sh 等），
  打包为 `prebuilt.tar.gz` 随配方提交，`build()` 中直接解包替代 `autoreconf`
- shebang 修正: `/bin/sh` → `/data/service/hnp/bin/bash`
- umask 077 移除: HMDFS 上 700 权限目录内无法创建文件
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

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL下载失败 | Savannah SSL证书验证失败 | 手动克隆 Git 仓库，创建 tarball |
| 2 | libtoolize失败 | HMDFS文件系统权限问题 | `LIBTOOLIZE=true autoreconf -fi` |
| 3 | automake失败 | HMDFS路径无法访问autoconf | 手动从 lib/Makefile.in 等复制模板 |
| 4 | configure缺辅助文件 | autoreconf未生成完整文件 | 从 libtool build-aux 复制 config.guess等 |
| 5 | G4缺少build_system | manifest模板使用嵌套字段 | 添加顶级 build_system: autotools |
| 6 | 本地验证动态库加载失败 | 共享库需要ELF签名 | 预编译包中已正确设置RPATH和签名 |
| 7 | CI流水线autoreconf失败 | CI worker无automake/libtoolize | 预生成autotools文件打包为prebuilt.tar.gz，build()中解包替代autoreconf |
| 8 | test_package运行找不到libtar.so | OHOS动态链接器不读conanrun的LD_LIBRARY_PATH | test()中手动设置LD_LIBRARY_PATH指向package_folder/lib |

## 知识提取

- **HMDFS权限问题**: libtoolize/automake 无法访问某些路径，需要使用环境变量绕过或手动创建文件
- **build_system字段**: manifest.yaml 需要顶级字段用于 G4 门禁检查

## 依赖版本

无外部依赖（zlib 为可选依赖，本次编译未启用）

## 验证结果

```bash
# libtar 无 make check 目标，通过功能性测试验证
# test_package 创建tar归档并读取验证内容一致性
```

**编译结束**: 2026-06-08 17:46
**最终状态**: built
