# vlock 2.2.2 适配笔记

## 软件与来源

- 软件：vlock 2.2.2（virtual console locking program，作者 Frank Benkstein）
- 上游状态：**原站已下线**（Debian #833843 "Upstream is dead"）；Debian 打包仓库
  `salsa.debian.org/debian/vlock` 保留 pristine 上游导入，使用标签 `upstream/2.2.2`。
- 源码 URL：
  `https://salsa.debian.org/debian/vlock/-/archive/upstream/2.2.2/vlock-upstream-2.2.2.tar.gz`
  SHA256 `5db15a875ead8f210a2fb3c57cda9001e43aed063b45a6126d1bb56d2f8422`（54754 B）
- 许可证：GPL-2.0-or-later（`src/auth-pam.c`、`src/prompt.[ch]` 为 BSD-3-clause 或 GPL-2）

## 编译环境

- 平台：HarmonyOS PC aarch64（`uname -s` = HarmonyOS，HongMeng Kernel 1.12.0）
- 编译器：clang 15.0.4（OHOS SDK），`--std=gnu99`
- Conan：2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 构建系统：上游自制 POSIX-sh `configure` + GNU make（**非 autotools**）
- 状态：`built`（conan create 通过，test_package 8/8）

## W0 依赖核验

| 依赖 | 用途 | 核验命令 | 结果 |
|------|------|----------|------|
| linux-pam/1.7.2 | PAM 认证后端（configure 默认 `AUTH_METHOD=pam`） | `conan download linux-pam/1.7.2 -r=ohpcd --only-recipe` / `conan install --requires=linux-pam/1.7.2` | ✅ recipe + binary 均可消费 |
| cunit/2.1-2 | 仅构建/运行上游测试套件 | `conan install --requires=cunit/2.1-2` | ✅ recipe + binary 均可消费 |

```text
$ bash ci/scripts/preflight_check.sh vlock/2.2.2 --deps "linux-pam/1.7.2 cunit/2.1-2"
[OK] 已发布: linux-pam/1.7.2
[OK] 已发布: cunit/2.1-2
[OK] 版本号未被占用: vlock/2.2.2
EXIT=0
```

## 编译步骤

```bash
cd <source_folder>          # vlock 2.2.2 解压目录
/bin/sh ./configure --prefix=<package_folder> --quiet CC=<clang> \
    ROOT_GROUP=root VLOCK_GROUP=root \
    EXTRA_CFLAGS="-I<linux-pam>/include -I<cunit>/include" \
    EXTRA_LDFLAGS="-L<linux-pam>/lib -L<cunit>/lib"
make -j1
make -C tests check -j1 CFLAGS="-O2 -Wall -W -pedantic -std=gnu99 -I<cunit>/include" \
    LDLIBS="-L<cunit>/lib -lcunit"
make install -j1 INSTALL=/bin/install
```

产物：`bin/vlock`（sh 启动脚本）、`sbin/vlock-main`（认证进程）、
`lib/vlock/modules/{all,new,nosysrq}.so`、`share/man/man{1,5,8}/*`。

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|----------------------|------|----------|
| 1 | `src/auth-pam.c:50:10: fatal error: 'security/pam_appl.h' file not found` | 未提供 linux-pam 头文件路径 | recipe `requirements()` 声明 `linux-pam/1.7.2`，并把其 include/lib 通过 `EXTRA_CFLAGS`/`EXTRA_LDFLAGS` 传入 |
| 2 | 链接 `vlock-main` 报 `undefined symbol: pam_start/pam_authenticate/...`（`pam libs:` 一行为空） | `configure` 的 `case "$OS" in Linux)` 不匹配 `uname` 输出的 "HarmonyOS" → `PAM_LIBS`/`DL_LIB`/`CRYPT_LIB`/`MODULES` 全空 | 补丁 `0001-configure.patch`：`Linux)` → `Linux|HarmonyOS)` |
| 3 | 重跑 configure 后 `pam libs` 仍为空 | `configure` 先 `parse_config_mk` 读取**上一次生成的 config.mk**，覆盖 `set_defaults` 的结果 | 生成前先 `rm -f config.mk`（recipe 为一次性干净构建，不受影响） |
| 4 | `make install` → `install: bad group 'vlock'` | 插件安装规则用 `-g $(VLOCK_GROUP)`（默认 "vlock"，发行版安装期才创建该组）；OHOS 无此组 | configure 传入 `VLOCK_GROUP=root`（同时 `ROOT_GROUP=root`，因 OHOS 无 `getent`） |
| 5 | `make install` → `make: install: No such file or directory` | OHOS 的 `install` 仅是 `/bin` 下的 toybox applet，`/bin` 不在默认 PATH | make 命令行显式 `INSTALL=/bin/install` |
| 6 | 构建套件段错误（CUnit 注册期崩溃） | 测试源码用 4 字段 `CU_SuiteInfo`；cunit/2.1-3 的 `CU_SuiteInfo` 在中间插入了 `pSetUpFunc`/`pTearDownFunc`，4 字段初始化器把 `CU_TestInfo[]` 赋给了 `pSetUpFunc`，`pTests` 保持 NULL | `test_requires("cunit/2.1-2")`（ABI 与测试源码一致） |
| 7 | conan create 中 `make` 编译 `vlock-main.o` 静默失败（clang 零输出、exit 1） | 本机沙箱对**由 python 直接派生**的进程链的 `execve` 敏感；同一命令由工具 shell 直接执行则正常 | 以 `<工具 shell → python(标准输入脚本) → 子进程>` 形态驱动构建链（见 `reports/test-report.md` §五） |

## 依赖版本

- linux-pam/1.7.2（链接：`vlock-main` DT_NEEDED 含 `libpam.so.0`）
- cunit/2.1-2（仅测试期，静态 `libcunit.a`）

## 验证结果

```bash
# 上游测试套件（真实执行）
$ make -C tests check
Run Summary:    Type  Total    Ran Passed Failed Inactive
              suites      4      4    n/a      0        0
               tests     14     14     13      1        0
             asserts     91     91     90      1      n/a
# 唯一失败项：test_process::test_wait_for_death（本机 exec 延迟导致 20 ms 窗口不足，环境限制）

# 消费者侧测试
$ python3 test_package/test_vlock.py <package_folder>
 CASE SUMMARY: total=8 passed=8 failed=0 skipped=0
 RESULT: PASS

# 配方自包含构建
$ conan create archives/v/vlock/2.2.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
### EXIT_CODE = 0
```

## 平台限制（HarmonyOS PC）

1. **虚拟控制台（VT）不可用**：`console_switch.c` 的 `VT_GETMODE`/`VT_SETMODE` 在
   HarmonyOS PC 上无对应设备节点，`lock_console_switch()` 会以
   `vlock: this terminal is not a virtual console`（ENOTTY/EINVAL）**干净失败并返回 false**，
   上游代码已处理该分支，无需改动；`-a/--all`（整机控制台锁定）因此在鸿蒙上不可用。
2. **`vlock-main` 需要 passwd 条目**：`src/vlock-main.c:217` 在 `getpwuid()` 失败时报
   `vlock: could not get username`。应用沙箱 uid（如 `20020084`）不在 `/etc/passwd` 中，
   故 `vlock-main` 仅对存在于 `/etc/passwd` 的账号可用。测试用例因此以
   `vlock` 启动脚本（`--version`/`--help`/非法选项）与 ELF/依赖闭包断言为主。
3. **属主/属组/置位位不保留**：HMDFS 上 `chown`/`chmod` 不生效，`install -o root -g root`
   与 `-m 4711` 均执行成功但不落盘为 root/SUID；Conan 包不承载系统安装期语义。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/vlock` | sh 启动脚本（`%BOURNE_SHELL%`=/bin/sh），解析选项并 exec `vlock-main` |
| `sbin/vlock-main` | 认证与锁屏进程（ELF64/LSB/AArch64，动态链接 `libpam.so.0`） |
| `lib/vlock/modules/*.so` | 插件：`all.so`、`new.so`、`nosysrq.so`（ELF aarch64 共享对象） |
| `share/man/man1,5,8` | vlock(1)、vlock-plugins(5)、vlock-main(8) |
| `licenses/COPYING` | GPL-2 许可证正文 |

## 注意事项

- 上游测试套件的 **test_wait_for_death** 属本机环境限制（见
  `reports/test-report.md`）；recipe 的 `build()` 会真实运行该套件，并**仅放行该项**
  已知环境限制失败，其余用例失败即令 conan create 失败。
- `cunit` 必须使用 **2.1-2**：2.1-3 的 `CU_SuiteInfo` 布局与上游测试源码不兼容。
---

**编译结束**: 2026-09-30 13:16
**最终状态**: built
