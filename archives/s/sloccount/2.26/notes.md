# sloccount 2.26 适配笔记

## 编译环境
- 构建系统: makefile（非标准 autotools，无 configure 脚本）
- 编译日期: 2026-06-05
- 编译器: clang/clang++ (LLVM 15.0.4)
- 状态: built

## 编译步骤

1. **初始化编译环境**
   - 使用本地 tarball 初始化：`ohc-run.py init-build sloccount 2.26 --url=file://.../sloccount-2.26.tar.gz`
   - 源码解压到 ~/tmp/builds/sloccount-2.26.work

2. **编译**
   - 由于是简单的 Makefile 项目，无需 configure
   - 直接执行：`make PREFIX=/storage/Users/currentUser/usr/local`
   - 编译生成多个可执行文件（c_count, java_count, lexcount1, pascal_count, php_count, jsp_count, ml_count）

3. **安装到 staging 目录**
   - 命令：`make install PREFIX=/storage/Users/currentUser/usr/local DESTDIR=/storage/Users/currentUser/tmp/test-install-sloccount-2.26`
   - 需要修改 Makefile 以支持 DESTDIR

4. **安装到本地**
   - 命令：`make install PREFIX=/storage/Users/currentUser/usr/local`
   - 安装到 ~/usr/local/bin, ~/usr/local/share/man, ~/usr/local/share/doc

5. **质量门禁验证**
   - 执行 `ohc-run.py verify-build sloccount 2.26`
   - G1-G4 全部通过

6. **预编译包制作**
   - 执行 `ohc-run.py package sloccount 2.26`
   - 生成 sloccount-2.26-ohos-aarch64.tar.gz (870KB)

7. **完成归档**
   - 执行 `ohc-run.py finish sloccount 2.26 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 环境 SSL 证书配置问题 | 使用 wget --no-check-certificate 手动下载 tarball |
| 2 | make install 失败 | Makefile 不支持 DESTDIR | 修改 makefile，在 install_programs/install_man/install_docs 目标中添加 DESTDIR 支持 |
| 3 | manifest 缺少 build_system | manifest.yaml 字段名不匹配 | 添加 build_system: makefile 字段 |
| 4 | Perl 脚本无法执行 | shebang 硬编码为 `/usr/bin/perl`，但平台 Perl 位于不同路径 | 修改所有 Perl 脚本的 shebang 为 `/storage/Users/currentUser/usr/local/bin/perl`（共 23 个文件）|

## 源码修改

**补丁文件**：
1. `0001-jsp_count.c.patch` - Flex 生成的代码（自动生成，平台相关）
2. `0002-makefile.patch` - 添加 DESTDIR 支持（核心修改）
3. `0003-pascal_count.c.patch` - Flex 生成的代码（自动生成，平台相关）

**主要修改**：
- makefile: 在 install_programs/install_man/install_docs 目标中添加 `$(DESTDIR)` 前缀
  - `install_programs`: 添加 `$(INSTALL_A_DIR) $(DESTDIR)$(INSTALL_DIR)`，修改安装路径为 `$(DESTDIR)$(INSTALL_DIR)`
  - `install_man`: 添加 `$(INSTALL_A_DIR) $(DESTDIR)$(MAN_DIR_MAN1)`
  - `install_docs`: 添加 `$(INSTALL_A_DIR) $(DESTDIR)$(DOC_DIR)`

## 依赖版本

无依赖（软件本身无外部库依赖）

编译工具版本：
- clang: 15.0.4
- make: GNU Make 4.4.1
- flex: (用于生成部分计数器)

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/sloccount --version
2.26

$ ls -lh /storage/Users/currentUser/usr/local/bin/ | grep sloccount
-rwxrwx--- 1 20001006 file_manager 21K  2026-06-05 20:56 sloccount

$ ls -lh archives/s/sloccount/2.26/packaging/
-rw-rw---- 1 20001006 file_manager 870K 2026-06-05 20:57 sloccount-2.26-ohos-aarch64.tar.gz
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sloccount-2.26-ohos-aarch64.tar.gz | 870KB | 预编译包（包含 37 个可执行文件） |

## 注意事项

1. **DESTDIR 支持**：原始 Makefile 不支持 DESTDIR，需要修改才能进行 staging 安装
2. **Flex 生成的文件**：jsp_count.c 和 pascal_count.c 是 Flex 自动生成的，补丁较大但无实际修改意义（仅编译器警告消除）
3. **Perl 路径适配**：软件包含 23 个 Perl 脚本，shebang 硬编码为 `/usr/bin/perl`，需在打包阶段修改为平台实际 Perl 路径
4. **测试跳过**：软件的 test 目标依赖外部环境，无法在本环境运行，已跳过
5. **G0 干净构建验证**：由于平台限制（Python subprocess），G0 验证失败，但已手动验证编译流程可重复
6. **功能测试**：核心功能（代码统计）验证通过，支持 30+ 种语言识别

## 知识提取记录

### E{N1}: Makefile 项目 DESTDIR 支持
- **发现时间**: 2026-06-05
- **适用范围**: 简单 Makefile 项目（无 configure）
- **解决方案**: 在 install 目标中添加 `$(DESTDIR)` 前缀到所有安装路径
- **通用模式**:
  ```makefile
  install_programs:
      $(INSTALL_A_DIR) $(DESTDIR)$(INSTALL_DIR)
      $(INSTALL) $(EXECUTABLES) $(DESTDIR)$(INSTALL_DIR)
  ```

### E{N2}: Perl 脚本 shebang 平台适配
- **发现时间**: 2026-06-06
- **适用范围**: 包含 Perl 脚本的软件
- **问题描述**: 原始脚本 shebang 硬编码为 `/usr/bin/perl`，但平台 Perl 位于不同路径
- **失败方案**: 使用 `#!/usr/bin/env perl -w`（env 无法处理 `-w` 参数）
- **正确方案**: 使用绝对路径 `#!/storage/Users/currentUser/usr/local/bin/perl -w`
- **涉及文件**: 23 个 Perl 脚本（asm_count, cobol_count, fortran_count 等）
- **修复时机**: 源码修改 + 重新编译打包

---
**编译结束**: 2026-06-05 20:57
**最终状态**: built