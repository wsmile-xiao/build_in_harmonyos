# ttyrec 1.0.8 适配笔记

## 编译环境
- 构建系统: makefile (简单 Makefile，无 configure)
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build ttyrec 1.0.8 --url=https://deb.debian.org/debian/pool/main/t/ttyrec/ttyrec_1.0.8.orig.tar.gz
   ```

2. 修改 Makefile 以支持鸿蒙环境
   - 使用环境变量中的 CC 和 CFLAGS
   - 添加 install 目标
   - 添加 PREFIX 和 DESTDIR 支持

3. 修复源码兼容性问题
   - ttyrec.c: 添加 `#include <fcntl.h>`（原代码仅在 SVR4 系统中包含）
   - ttyrec.c: 将 `union wait status` 改为 `int status`（现代系统不支持 union wait）
   - ttyrec.c: 删除旧式 `char *getenv()` 声明

4. 编译和安装
   ```bash
   cd /storage/Users/currentUser/tmp/builds/ttyrec-1.0.8.work
   make -j1
   make install DESTDIR=/storage/Users/currentUser/tmp/test-install-ttyrec-1.0.8 PREFIX=/storage/Users/currentUser/usr/local
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|## 知识提取

### L1 平台真理
1. **旧式 BSD 代码适配**：`union wait` 类型在现代系统（包括 OpenHarmony）中已废弃，应统一使用 `int status`。
   - 错误特征：`variable has incomplete type 'union wait'`
   - 解决方案：删除 SVR4 条件编译，统一使用 `int status`

2. **fcntl.h 必需性**：`O_RDWR` 等常量定义在所有 POSIX 系统都需要 `<fcntl.h>`，不应仅在 SVR4 系统中包含。
   - 错误特征：`use of undeclared identifier 'O_RDWR'`
   - 解决方案：无条件包含 `<fcntl.h>`

### L2 模式经验
1. **无 configure 的 Makefile 项目**：简单 Makefile 项目需要手动添加以下支持：
   - 使用 `?=` 条件赋值支持环境变量覆盖
   - 添加 `PREFIX` 变量（默认 `/usr/local`）
   - 添加 `install` 目标（支持 `DESTDIR` 和 `PREFIX`）
   - 添加 man 页面安装

---|------|------|----------|
| 1 | `union wait` 类型不完整 | BSD 旧式用法，现代系统已废弃 | 改为 `int status` |
| 2 | `O_RDWR` 未定义 | 缺少 `<fcntl.h>` 包含 | 无条件包含 `<fcntl.h>` |
| 3 | `getenv()` 重复声明 | 旧式声明与标准库冲突 | 删除旧式声明 |
| 4 | 无 configure 脚本 | 项目使用简单 Makefile | 手动修改 Makefile |

## 源码修改

### Makefile
- 添加 `?=` 条件赋值支持环境变量
- 添加 `PREFIX` 变量
- 添加 `install` 目标
- 调整格式一致性

### ttyrec.c
- 第 57 行：添加 `#include <fcntl.h>`
- 第 58-61 行：移除 SVR4 条件，移除 `#include <stropts.h>`
- 第 206-210 行：删除 `union wait` 条件编译，统一使用 `int status`
- 第 124 行：删除 `char *getenv()` 旧式声明

## 依赖版本

无外部依赖，仅需标准 C 库。

## 验证结果

```bash
# 编译成功，生成三个可执行文件
ls -lh /storage/Users/currentUser/tmp/test-install-ttyrec-1.0.8/storage/Users/currentUser/usr/local/bin/
# ttyrec, ttyplay, ttytime

# 无 make check 目标，跳过测试
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ttyrec-1.0.8-ohos-aarch64.tar.gz | 250KB | 预编译包 |
| ttyrec-1.0.8-ohos-aarch64-debug.tar.gz | 80KB | 调试符号包 |

## 注意事项

1. 此项目无 configure 脚本，需手动修改 Makefile
2. 源码包含旧式 BSD 代码，需要适配现代系统
3. 编译时有警告但不影响功能
4. 无测试套件
---

**编译结束**: 2026-06-08 18:11
**最终状态**: built
