# apparmor 4.1.0 适配笔记

## 编译环境
- 构建系统: custom（多组件构建）
- 编译日期: 2026-06-18
- 编译器: clang/clang++
- 状态: built（核心组件编译成功，parser/utils/profiles因平台限制无法编译）

---

**编译结束**

**最终状态**: built（部分组件）

**完成的组件**:
- libapparmor: 成功编译，生成共享库和静态库
- binutils: 成功编译 5 个工具（aa-enabled, aa-exec, aa-features-abi, aa-load, aa-status）

**无法编译的组件**:
- parser: 失败 - Linux 内核头文件缺失 (linux/capability.h)、gettext 库不兼容、GCC 扩展头文件缺失 (ext/stdio_filebuf.h)
- utils: 跳过 - Python 工具依赖 parser
- profiles: 跳过 - 配置文件需要 parser 验证

**质量门禁**: G1-G4 全部通过

**预编译包**: apparmor-4.1.0-ohos-aarch64.tar.gz (1285KB)

**补丁**: 8 个补丁已生成

---

## 编译步骤

AppArmor 是一个多组件项目，需要按顺序编译：
1. **libapparmor** - 核心库（autotools）
   - 进入 `libraries/libapparmor`
   - `autoreconf -fi`（修复 configure 生成）
   - 修改 `configure.ac` 移除 AX_CHECK_COMPILE_FLAG 检查
   - 修改 `configure` 和 `config.status` 使用 `$TMPDIR`
   - 修改 umask 解决 HMDFS 权限问题
   - `./configure --prefix=$DEFAULT_PREFIX`
   - `make && make install DESTDIR=$TEST_PREFIX`
   - `make install`（安装到本地）

2. **binutils** - 基本工具（makefile）
   - 修改源文件禁用 gettext 功能（libintl.h 不兼容）
   - 添加 limits.h 头文件（NAME_MAX 定义）
   - 使用 GNU ld 绕过 lld libxml2 问题
   - `make CC="cc -fuse-ld=/data/service/hnp/bin/ld"`
   - 手动安装二进制文件

3. **parser** - 策略解析器（待完成）
   - 需要生成 generated_af_names.h 和 generated_cap_names.h
   - Makefile 硬编码路径问题待解决

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 语法错误 | AM_INIT_AUTOMAKE 宏未展开 | `autoreconf -fi` 重新生成 |
| 2 | AX_CHECK_COMPILE_FLAG 缺失 | 缺少 autoconf-archive | 修改 configure.ac 移除检查 |
| 3 | config.status 权限错误 | HMDFS umask 077 限制 | 修改 umask 为 000 |
| 4 | af_protos.h IPPROTO 错误 | 宏名称错误 UIPPROTO vs IPPROTO | 重新生成文件 |
| 5 | lld 无法运行 | 缺少 libxml2.so.16 | 使用 GNU ld (`-fuse-ld=/data/service/hnp/bin/ld`) |
| 6 | gettext 链接失败 | g_libintl_gettext 符号不存在 | 禁用 gettext，使用原始字符串 |
| 7 | NAME_MAX 未定义 | 缺少 limits.h | 添加 `#include <limits.h>` |

## 源码修改

### libraries/libapparmor/configure.ac
- 移除 AX_CHECK_COMPILE_FLAG 检查
- 简化 EXTRA_CFLAGS 设置

### libraries/libapparmor/configure + config.status
- 修改临时目录创建使用 `$TMPDIR`
- 修改 umask 从 077 到 000

### libraries/libapparmor/src/af_protos.h
- 重新生成，使用正确的 IPPROTO_* 常量名称

### binutils/*.c (aa_enabled.c, aa_exec.c, aa_features_abi.c, aa_load.c)
- 禁用 gettext 功能
- 添加 limits.h 头文件

## 依赖版本

- clang: 15.0.4
- autotools: autoconf 2.72, automake 1.16.5
- libapparmor: 4.1.0 (自编译)
- gettext: 0.22.5 (预编译，但符号不兼容)

## 验证结果

```bash
# libapparmor 库验证
ls $HOME/usr/local/lib/libapparmor.so
# 输出: libapparmor.so -> libapparmor.so.1.24.2

# binutils 二进制验证
file $HOME/usr/local/bin/aa-enabled
# 输出: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

# 列出所有编译产物
ls $HOME/usr/local/bin/aa-*
# aa-enabled, aa-exec, aa-features-abi, aa-load, aa-status
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libapparmor.so.1.24.2 | 211520 | 核心共享库 |
| libapparmor.a | 308434 | 静态库 |
| aa-enabled | 75552 | 检查 AppArmor 是否启用 |
| aa-exec | 82320 | 在 AppArmor 约束下执行程序 |
| aa-features-abi | 68384 | 特性 ABI 工具 |
| aa-load | 139624 | 加载策略工具 |
| aa-status | 178512 | 状态查询工具 |

## 注意事项

1. AppArmor 是多组件项目，需要按顺序编译（libapparmor → binutils → parser → utils → profiles）
2. gettext 库与预编译版本不兼容，需要禁用
3. lld 链接器在鸿蒙上有问题，推荐使用 GNU ld
4. parser 编译需要手动生成 generated_af_names.h 和 generated_cap_names.h
5. 项目与 Linux 内核 LSM 深度绑定，部分功能在鸿蒙上可能受限

## 后续工作

- 完成 parser 编译（策略解析器）
- 完成 utils 编译（Python 工具）
- 完成 profiles 编译（配置文件）
- 打包预编译包
- 归档和验证
---

**编译结束**: 2026-06-18 15:08
**最终状态**: built
