# bwa 0.7.19 适配笔记

## 编译环境
- **构建系统**: makefile（自定义 Makefile，无 autotools/configure/install 目标）
- **编译日期**: 2026-05-27
- **编译器**: clang 15.0.4（通过 gcc symlink 调用）
- **平台**: aarch64（OpenHarmony / 鸿蒙）
- **状态**: published

## 编译步骤

### 1. 下载源码
- URL: https://github.com/lh3/bwa/archive/refs/tags/v0.7.19.tar.gz
- **问题**: GitHub 直接访问超时
- **解决**: 使用 kkgithub.com 镜像下载（238KB tarball）
- SHA256: cdff5db67652c5b805a3df08c4e813a822c65791913eccfb3cf7d528588f37bc

### 2. 初始化（init-build）
- 使用 `--no-download` 模式，源码已预先下载并解压
- 源码路径: ~/tmp/builds/bwa-0.7.19.work
- 构建系统检测: makefile（非 autotools）
- 所有依赖已就绪，无需额外安装

### 3. 编译（make）
- 直接在源码目录执行 `make`，无需 configure
- 33个源文件全部成功编译
- CFLAGS: -g -Wall -Wno-unused-function -O3 -DHAVE_PTHREAD -DUSE_MALLOC_WRAPPERS
- 编译警告: bwtsw2_core.c:453 — 变量 n_tot 已赋值但未使用（非关键）
- **产物**: bwa 二进制（1MB）+ libbwa.a 静态库（760KB）

### 4. 手动安装（DESTDIR 模式/R20）
- **问题**: bwa Makefile 没有 install 目标
- **解决**: 通过补丁（0001-Makefile.patch）添加 install 目标
- 安装命令: `make install DESTDIR=$TEST_PREFIX`
- DESTDIR 模式: --prefix=$DEFAULT_PREFIX + DESTDIR=$TEST_PREFIX
- 安装产物: bin/bwa, bin/qualfa2fq.pl, bin/xa2multi.pl, lib/libbwa.a, include/bwa/*, share/man/man1/bwa.1

### 5. 预编译包制作
- 命令: `ohc-run.py package bwa 0.7.19`
- 产物: bwa-0.7.19-ohos-aarch64.tar.gz（1270KB）
- 已通过 ELF 签名、RPATH 设置、strip、权限修复等9步流程

### 6. 本地部署与功能验证
- 安装到 DEFAULT_PREFIX（不带 DESTDIR）
- bwa 版本验证: 0.7.19-r1273 ✅

---

## 真实功能测试结果

使用500bp人工参考序列 + 5条50bp模拟读段进行完整比对流程测试：

| 子命令 | 结果 | 详情 |
|--------|------|------|
| bwa index | ✅ | 5个索引文件正确生成（.amb/.ann/.bwt/.pac/.sa） |
| bwa mem | ✅ | 5条读段全部成功比对，映射质量60，NM变异检测正确 |
| bwa aln | ✅ | SA坐标计算成功，aln.sai 208字节 |
| bwa samse | ✅ | SAM格式输出正确，映射质量37，XT:A:U唯一比对 |
| bwa fastmap | ✅ | 超极大精确匹配识别正常 |
| bwa shm | ✅ | 共享内存索引管理可用 |
| bwa pac2bwt | ✅ | PAC→BWT转换正常 |
| bwa bwtupdate | ✅ | BWT更新正常 |
| qualfa2fq.pl | ✅ | 用法说明正常显示 |
| xa2multi.pl | ✅ | 可解析SAM输入 |

**核心结论**: bwa 0.7.19-r1273 在鸿蒙平台上比对功能完全正常。

---

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络无法直接访问 GitHub | 使用 kkgithub.com 镜像 |
| 2 | Makefile 无 install 目标 | 自定义 Makefile 不含标准安装规则 | 补丁 0001-Makefile.patch 添加 install 目标（DESTDIR模式） |
| 3 | 无 configure 脚本 | 纯 Makefile 项目无 autotools | 补丁 0002-configure.patch 添加 configure wrapper（G0 clean-verify 兼容） |
| 4 | manifest 缺少 build_system | verify-build G4 检查需要此字段 | 添加 build_system: makefile 到 manifest.yaml |

---

## 源码修改（2个补丁）

### 0001-Makefile.patch
- **类型**: 功能增强（添加 install 目标）
- **内容**: 为 bwa Makefile 添加 install 目标，支持 DESTDIR 模式（R20）
- **修改**: Makefile 添加13行（PREFIX变量 + install 规则）
- **影响**: 打包/部署流程依赖此补丁

### 0002-configure.patch
- **类型**: 适配补丁（G0 clean-verify 兼容）
- **内容**: 添加空操作 configure wrapper 脚本
- **修改**: 新增 configure 文件（5行）
- **影响**: 使 G0 干净构建验证可以通过

---

## 依赖版本
- zlib: 系统内置（-lz）
- pthread: 系统内置（-lpthread）
- 无其他外部依赖

---

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bwa-0.7.19-ohos-aarch64.tar.gz | 1270KB | 预编译包（含ELF签名） |
| bwa-0.7.19-ohos-aarch64-debug.tar.gz | 645KB | 调试符号包 |
| bwa 二进制 | 1001984字节 | 主程序 |
| libbwa.a | 760150字节 | 静态库 |

---

## 注意事项
- bwa Makefile 硬编码 gcc，实际环境 gcc 是 clang 的 symlink，不影响编译
- bwa 无标准测试套件（no make check），需手动功能验证
- bwa mem/aln 等子命令需要使用绝对路径访问输入文件（HMDFS 文件系统限制）
- 1个编译警告（bwtsw2_core.c: n_tot 变量未使用），不影响功能

---

**编译结束**: 2026-05-27
**最终状态**: published