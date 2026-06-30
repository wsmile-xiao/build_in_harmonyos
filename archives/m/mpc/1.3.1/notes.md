# mpc 1.3.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-08
- 编译器: clang 15.0.4
- 状态: built（编译成功，仅提供静态库）

## 编译步骤

本次编译采用手动编译方式，绕过了 libtool 的问题：

1. **下载源码**：从阿里云镜像下载 mpc-1.3.1.tar.gz
2. **安装依赖**：使用 cmd-pkgs 安装 gmp 6.3.0 和 mpfr 4.2.1 预编译包
3. **解压源码**：解压到 ~/builds/mpc-1.3.1.work
4. **修复配置脚本**：
   - 使用 patch-autotools-ohos.pl 修复 config.guess 和 config.sub
   - 手动修改 config.sub 添加 linux-ohos* 到 kernel-os 白名单（第1775行）
   - 修改 configure 和 config.status 的临时目录逻辑
5. **配置编译**：
   ```bash
   export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
   export CFLAGS="-I/storage/Users/currentUser/usr/local/include"
   export LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"
   export TMPDIR=/storage/Users/currentUser
   ./configure --prefix=/storage/Users/currentUser/usr/local
   ```
6. **修改 config.status**：将临时目录从 mktemp 改为固定路径
7. **运行 config.status**：生成 Makefile 和 config.h
8. **编译源码**：`make -j4`，编译所有源文件
9. **创建静态库**：绕过 libtool，直接使用 `ar rcs libmpc.a *.o`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统类型 | 原始脚本未包含 HarmonyOS 检测逻辑 | 使用 patch-autotools-ohos.pl 添加 __OHOS__ 宏检测 |
| 2 | config.sub 三元组验证失败 | kernel-os 白名单缺少 linux-ohos* | 手动添加 `linux-ohos*` 到第1775行的白名单 |
| 3 | 缺少 gmp.h 头文件 | 未设置 CFLAGS 指向 gmp 安装路径 | 设置 `CFLAGS="-I/storage/Users/currentUser/usr/local/include"` |
| 4 | config.status 临时目录权限错误 | mktemp 在当前目录创建临时文件权限不足 | 修改临时目录为 `/storage/Users/currentUser/mpc-work-tmp` |
| 5 | 缺少 config.h.in 文件 | 源码目录被清理时误删 | 从 .orig 目录复制 config.h.in |
| 6 | libtool 报错 libgmp.la 无效 | 预编译包缺少 libgmp.la 文件 | 手动创建 libgmp.la，但仍失败；最终绕过 libtool |
| 7 | libtool 验证 libgmp.la 失败 | libgmp.la 格式不符合 libtool 要求 | 直接使用 `ar rcs libmpc.a *.o` 创建静态库 |

## 源码修改

应用了 4 个补丁：

1. **0001-build-aux-config.guess.patch** (+11/-0)
   - 添加 HarmonyOS 系统识别（__OHOS__ 宏检测）
   - 输出三元组：`aarch64-unknown-linux-ohos`

2. **0002-build-aux-config.sub.patch** (+8/-2)
   - 在 kernel-os 白名单添加 `linux-ohos*`
   - 修复 "Kernel 'linux' not known to work with OS 'ohos'" 错误

3. **0003-config.status.patch** (+2004/-0)
   - 新增文件（原来不存在）
   - 修改临时目录创建逻辑为固定路径

4. **0004-configure.patch** (+1/-1)
   - 修改 mktemp 的临时目录路径为绝对路径
   - 避免权限不足问题

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| GMP | 6.3.0 | cmd-pkgs 预编译包 |
| MPFR | 4.2.1 | cmd-pkgs 预编译包 |
| clang | 15.0.4 | 系统预装 |
| Make | 4.4.1 | GNU Make |

## 验证结果

```bash
# 验证静态库创建
cd /storage/Users/currentUser/builds/mpc-1.3.1.work/src
ls -la libmpc.a
# -rw-rw---- 1 20001006 file_manager 329642 2026-06-05 17:53 libmpc.a

# 验证库文件类型
file libmpc.a
# libmpc.a: ar archive

# 验证头文件
ls -la mpc.h
# -rw-rw---- 1 20001006 file_manager 16949 2026-06-05 17:53 mpc.h

# Strip 后大小
llvm-strip --strip-debug libmpc.a
ls -lh libmpc.a
# -rw-rw---- 1 20001006 file_manager 319K 2026-06-08 11:37 libmpc.a
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mpc-1.3.1-ohos-aarch64.tar.gz | 10KB | 预编译制品包（静态库） |
| lib/libmpc.a | 319KB | 静态库（已 strip） |
| include/mpc.h | 16KB | 头文件 |
| patches/*.patch | 4 个 | 源码补丁 |

## 注意事项

1. **仅静态库**：本版本仅提供静态库（libmpc.a），不提供共享库（libmpc.so）。原因是 libtool 在处理预编译 gmp 包时遇到兼容性问题。

2. **手动设置环境变量**：编译依赖 mpc 的程序时，必须设置 CFLAGS 和 LDFLAGS：
   ```bash
   export CFLAGS="-I~/usr/local/include"
   export LDFLAGS="-L~/usr/local/lib"
   ```

3. **依赖安装**：使用前必须先安装 gmp 和 mpfr：
   ```bash
   curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gmp 6.3.0
   curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- mpfr 4.2.1
   ```

4. **缺少 pkg-config 文件**：预编译包未包含 mpc.pc，需要手动创建（参考 README.md）

5. **质量门禁未完成**：本次为手动编译，未执行 make check 和完整的质量门禁验证流程（G0-G4）

6. **建议改进**：
   - gmp 预编译包应包含 libgmp.la 文件以支持 libtool 链接
   - 技能应自动设置 CFLAGS/LDFLAGS 指向已安装依赖的路径
   - 将临时目录权限问题添加为新的知识图谱错误模式（建议编号 E091）

---

**编译开始**: 2026-06-05 17:37
**编译结束**: 2026-06-08 11:39
**最终状态**: built（编译成功，静态库）