# pacapt 3.0.7 适配笔记

## 编译环境
- 构建系统: custom (shell script concatenation)
- 编译日期: 2026-09-07
- 编译器: 无（纯 shell 脚本）
- 状态: built

## 编译步骤

pacapt 是纯 POSIX shell 脚本，无需 C/C++ 编译。构建过程为 shell 脚本拼接：

```bash
# 设置 VERSION 环境变量（tarball 无 .git 目录，compile.sh 需要此变量）
VERSION=3.0.7 bash bin/compile.sh
```

产出物是单个 `pacapt` shell 脚本（约 56KB），可直接安装到 PATH。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bin/compile.sh 需要 git 获取版本 hash | tarball 解压后无 .git 目录 | 通过环境变量 `VERSION=3.0.7` 显式传入 |
| 2 | 上游测试需要 Docker | tests/ 使用 Docker 容器运行真实包管理器 | 仅做 smoke test（文件存在性 + 语法检查 + 版本字符串） |

## 依赖版本

无编译时依赖。运行时需要 POSIX sh 环境。

## 测试结果

### conan create 全流程
- 源码下载 ✅（SHA256 匹配）
- bin/compile.sh 拼接 ✅（57,765 字节，`pacapt version '3.0.7' has been generated`）
- package() 打包 ✅
- test_package ✅（9 pass, 0 fail, 13 skip in Layer 0-3; 6 pass, 3 fail in Layer 4）

### 上游测试覆盖
- 上游 12 个测试文件，310 条命令，**全部无法运行**
- 根因：OHOS 无任何系统包管理器（dpkg/apk/yum/dnf/zypper 等），且无 Docker
- 已在 test_package MANIFEST.yml 和 test-report.md 中记录

### pip 后端功能测试（Layer 4，新增）
- 通过 `pacman-pip` 命名法绕过 `_PACMAN_detect`
- 利用 OHOS 上已有的 pip 24.3.1 真实调用 pacapt pip 后端
- 9 项测试：6 通过，3 失败（pacapt pip 后端未实现 Qi/Ss/Si，属上游功能限制）

## 验证结果

```bash
# conan create 全流程
conan create archives/p/pacapt/3.0.7 --version 3.0.7

# pip 后端功能测试
cp ~/.conan2/p/b/pacap*/p/bin/pacapt ~/bin/pacman-pip
sh ~/bin/pacman-pip -V       # → "pacapt version '3.0.7'"
sh ~/bin/pacman-pip -Q       # → 真实调用 pip list
sh ~/bin/pacman-pip -Qs pip  # → 真实调用 pip list + grep
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/pacapt | ~57KB | pacman-like 包管理器 wrapper shell 脚本 |

## 注意事项

- pacapt 是纯 shell 脚本，不涉及 C/C++ 编译、链接、交叉编译等流程
- shebang 为 `#!/usr/bin/env sh`，OHOS 平台需确保 `/usr/bin/env` 存在
- OHOS 无系统包管理器，`_PACMAN_detect` 默认会失败；可通过 `pacman-pip` 命名法使用 pip 后端
- 上游测试体系（Docker + 真实包管理器）完全不适用于 OHOS CI 环境
- pacapt pip 后端仅支持 -Q/-Qs/-Sc 等子集操作，-Qi/-Ss/-Si 未实现

---

**编译结束**: 2026-09-07
**最终状态**: built
