# 编译记录：psmisc 23.6

**编译开始**: 2026-04-28

## 源码获取

- 源码包: psmisc_23.6.orig.tar.xz
- 来源: https://deb.debian.org/debian/pool/main/p/psmisc/
- 解压: ~/tmp/psmisc-build/

## 依赖安装

- ncurses 6.4: 已安装（预编译包）
  - `curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- ncurses 6.4`

## 编译过程

### 问题1: config.guess 无法识别系统类型

**原因**: TMPDIR=/tmp 只读，无法创建临时文件
**解决**: 修改 config.guess 中的 TMPDIR 默认值为 $HOME/tmp

### 问题2: config.status 无法创建临时文件

**原因**: HMDFS 文件系统权限限制，即使在可写目录中也无法创建临时文件
**尝试**: 修改 config.status 使用 TMPDIR，但仍然失败

### 问题3: configure 运行超时

**原因**: configure 脚本在多项测试中运行缓慢（可能是某些系统调用受限）
**解决**: 手动创建 config.h 并直接编译

## 最终编译方案

手动创建 config.h 并使用 clang 直接编译：

```bash
cd ~/tmp/psmisc-build
cat > config.h <<'EOF'
#define PACKAGE_NAME "psmisc"
#define PACKAGE_VERSION "23.6"
#define VERSION "23.6"
...
EOF
clang -include config.h -I~/usr/local/include -L~/usr/local/lib -o pstree src/pstree.c -lncursesw
```

**编译结果**: 成功
**验证**: `./pstree -V` 输出正确版本信息

## 平台限制发现

1. `/proc/uptime` 权限受限（Permission denied）
2. HMDFS 临时文件创建权限问题（即使在可写目录中）
3. config.guess/config.status 依赖临时文件创建

**编译结束**: 2026-04-28
**最终状态**: partial（手动编译成功，但 configure 流程未能完成）
---

**编译结束**: 2026-04-28 04:11
**最终状态**: partial
