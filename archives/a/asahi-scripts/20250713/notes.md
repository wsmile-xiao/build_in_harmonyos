# asahi-scripts 20250713 适配笔记

## 编译环境
- 构建系统: makefile (pure shell scripts, no compilation)
- 编译日期: 2026-08-19
- 编译器: N/A (shell scripts only, no C/C++ compilation)
- 状态: built

## 编译步骤

1. `init-build` — 下载并解压 asahi-scripts 20250713 源码
2. `make all` — Makefile `all` 目标使用 `sed` 处理脚本（替换配置路径）
3. `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX` — 安装脚本到 staging 目录

### 关键命令
```bash
source .build-context-asahi-scripts-20250713
cd $BUILD_SRC_DIR
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
```

### 产物布局
- `bin/asahi-diagnose` — 系统诊断脚本
- `bin/asahi-fwupdate` — 固件更新脚本
- `bin/update-m1n1` — m1n1 bootloader 更新脚本
- `bin/functions.sh` — 公共函数库（安装在 bin/ 供脚本查找）
- `share/asahi-scripts/functions.sh` — 公共函数库（标准路径）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make install` 失败：`make: install: No such file or directory` | HarmonyOS 无 coreutils `install` 命令 | 创建 `/storage/Users/currentUser/usr/local/bin/install` POSIX shell wrapper 脚本，支持 `-d`、`-dD`、`-mMODE -t DIR` 等用法 |
| 2 | install wrapper 脚本无法执行 | 初始使用 `#!/bin/bash`，但 HarmonyOS 无 `/bin/bash` | 改用 `#!/bin/sh`（POSIX 兼容）并移除 bash 数组语法 |
| 3 | `-dD` 组合参数未正确处理 | case 语句未处理合并的短选项 | 重写 case 匹配逻辑支持 `-dD`、`-Dd` 等组合 |
| 4 | conanfile.py 模板不匹配 | init-build 自动生成的 autotools 模板（有 configure/make）不适用于纯 shell 脚本项目 | 手动重写 conanfile.py：package_type=application、build() 只跑 make all、package() 用 copy() 安装、package_info() 用 bindirs |

## 源码修改

无补丁。源码无需修改即可在 HarmonyOS 上安装运行。
脚本使用 `#!/bin/sh`，与 HarmonyOS `/bin/sh` (mksh) 兼容。
`asahi-diagnose` 在 HarmonyOS 上可正常运行（部分 /proc/device-tree 路径不存在但脚本优雅处理）。

## 依赖版本

无依赖。纯 shell 脚本项目。

## 验证结果

```bash
# make install 成功
$ make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
# 安装 4 个文件：3 个脚本 + functions.sh

# asahi-diagnose 可执行
$ /bin/sh build/asahi-diagnose 2>&1 | head -5
# 输出: "Collecting system diagnostic information..."
# 输出: "Saved diagnostic information to ..."
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（Makefile 构建系统，application 类型） |
| conandata.yml | 源码 URL + SHA256 |
| test_package/test.sh | 冒烟测试：执行 asahi-diagnose 并验证输出 |
| commands.json (软件级) | 命令行工具声明（R38） |

## 注意事项

1. **install 命令**: HarmonyOS 缺少 coreutils `install` 命令。conanfile.py 的 `package()` 方法使用 Conan 的 `copy()` 工具代替 `make install`，避免依赖系统 `install` 命令。
2. **whoami 命令**: `asahi-diagnose` 脚本调用 `whoami`，HarmonyOS 上不可用，但不影响脚本执行（输出为空，脚本无 `set -e`）。
3. **/proc/device-tree**: 部分 device-tree 路径在 HarmonyOS 上不存在或权限不足，脚本优雅处理（输出 "(missing)" 或跳过）。
4. **functions.sh 位置**: 脚本先检查 `$(dirname "$0")/functions.sh`，因此 conan package 将 functions.sh 复制到 bin/ 目录。
---

**编译结束**: 2026-08-19 14:44
**最终状态**: built
