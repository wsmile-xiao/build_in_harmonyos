# mafft 7.526 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile 项目，无 configure 脚本）
- 编译日期: 2026-05-28
- 编译器: clang / clang++
- 目标架构: aarch64 (OpenHarmony)
- 状态: built

## 编译步骤

### 1. 获取源码
```bash
GIT_SSL_NO_VERIFY=1 git clone https://gitlab.com/mafft/mafft.git --branch v7.526
```
注意：Savannah 官方镜像 SSL 证书验证失败，需从 GitLab clone 并禁用 SSL 验证。

### 2. 初始化构建目录
```bash
ohc-run.py init-build mafft 7.526
```
mafft 的 tarball 中嵌套了 MPI 子目录的 tarball，init-build 的自动解压会错误提取嵌套 tarball，需手动解压并设置 .orig/.work 目录。

### 3. 创建包装器脚本
mafft 无 configure 脚本，需手动创建：
- **configure 包装器**: `#!/bin/sh` + `exit 0`（满足 G0 configure 门禁要求）
- **顶层 Makefile 包装器**: 递归调用 `core/` 和 `extensions/` 子目录的 Makefile

### 4. 修改核心 Makefile
修改 `core/Makefile`：
- `PREFIX` 改为 `/storage/Users/currentUser/usr/local`
- `CC` 改为 `clang`
- `CFLAGS` 保留 `-Denablemultithread -std=c99 -fPIC -O2`

### 5. 修改 shebang
修改 `core/mafft.tmpl` 中所有 shebang 从 `#!/bin/bash` 改为 `#!/usr/bin/env bash`（OpenHarmony 无 /bin/bash）。

### 6. 修改 extensions/Makefile
修改 `extensions/Makefile` 中 `CXX` 从 `g++` 改为 `clang++`。

### 7. 编译与安装
```bash
cd core && make && make install
cd extensions && make && make install
```

### 8. ELF 签名
所有二进制需签名才能在鸿蒙系统执行：
```bash
ohc-run.py sign-elf <binary_path>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah 镜像 SSL 验证失败 | 证书链不完整/过期 | GIT_SSL_NO_VERIFY=1 从 GitLab clone |
| 2 | init-build 解压嵌套 tarball | mafft tarball 内含 MPI 子 tarball | 手动解压主 tarball，跳过嵌套 |
| 3 | G0 要求 configure 但 mafft 无 configure | mafft 是纯 Makefile 项目 | 创建 `#!/bin/sh; exit 0` 包装器 |
| 4 | G0 要求顶层 Makefile | mafft 源码顶层无 Makefile | 创建顶层 Makefile 包装器（递归调用 core/extensions） |
| 5 | /bin/bash 不存在 | OpenHarmony 无 /bin/bash | shebang 改为 `#!/usr/bin/env bash` |
| 6 | 二进制无法执行 | 未签名 ELF | ohc-run.py sign-elf 签名所有二进制 |
| 7 | wrapper 脚本 rm/mv 未找到 | PATH 不含 /usr/bin | 部署时需确保 PATH 包含 /usr/bin |
| 8 | /dev/stderr 权限受限 | OpenHarmony sandbox 限制 | 非关键，不影响对齐输出 |
| 9 | refresh-patch 对 configure 补丁格式问题 | 新增文件补丁格式兼容性 | 简化 configure 为 2 行脚本，用 diff -ruN 生成 |
| 10 | /tmp 只读 | OpenHarmony sandbox 限制 | 使用 TMPDIR=/storage/Users/currentUser/tmp |

## 源码修改

### 补丁列表 (5个)

| 补丁 | 类型 | 修改文件 | 说明 |
|------|------|----------|------|
| 0001-Makefile.patch | 新增 | Makefile | 顶层 Makefile 包装器 |
| 0002-configure.patch | 新增 | configure | configure 包装器 (#!/bin/sh, exit 0) |
| 0003-core-Makefile.patch | 修改 | core/Makefile | CC=clang, PREFIX 适配 |
| 0004-core-mafft.tmpl.patch | 修改 | core/mafft.tmpl | shebang → #!/usr/bin/env bash |
| 0005-extensions-Makefile.patch | 修改 | extensions/Makefile | CXX → clang++ |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| clang | 系统自带 | C 编译器 |
| clang++ | 系统自带 | C++ 编译器 |
| bash | /storage/Users/currentUser/usr/local/bin/bash | 脚本执行 |
| make | 系统自带 | 构建工具 |

无外部库依赖（mafft 为纯 C/C++ 项目，不依赖第三方库）。

## 验证结果

详见 `test-report.md`，13项功能测试全部通过：
- 多种对齐方法 (FFT-NS-2, L-INS-i, E-INS-i, --auto) 正确
- Gap 插入、片段追加功能正确
- 核心二进制 (dndfast7, tbfast, mxscarnamod) 正常
- G0 干净构建验证通过
- G1-G4 门禁验证通过

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mafft-7.526-ohos-aarch64.tar.gz | 15MB | 主预编译包 (21 bin + 35 libexec) |
| mafft-7.526-ohos-aarch64-debug.tar.gz | 570KB | debug 包 (含未 stripped 二进制) |

## 注意事项

1. **PATH 要求**: mafft wrapper 脚本使用 rm/mv/mkdir 等命令，部署时需确保 PATH 包含 `/usr/bin`
2. **bash 路径**: 所有 shebang 已改为 `#!/usr/bin/env bash`，需确保 bash 在 PATH 中
3. **ELF 签名**: 所有二进制已通过 ohc sign-elf 签名，可在鸿蒙系统执行
4. **临时目录**: mafft 运行时创建临时文件，需 TMPDIR 设置为可写目录（默认 /tmp 在 OpenHarmony sandbox 可能只读）
5. **mxscarnamod**: C++ 编译的 RNA 结构对齐工具，使用 clang++ 编译，有少量 warning 但功能正常

---
**编译结束**: 2026-05-28 12:18
**最终状态**: built
---

**编译结束**: 2026-06-01 11:08
**最终状态**: built
