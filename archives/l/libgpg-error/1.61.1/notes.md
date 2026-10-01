# libgpg-error 1.61.1 适配笔记（OHOS / 鸿蒙 PC）

> R37 迭代版本：1.61.1 的**上游源码仍为 libgpg-error-1.61 官方 tarball**，
> 仅以 1.61.1 版本号承载 1.61 已在 main 合入并发布 ohpcd 的适配方案
> （cnb.cool 制品仓不支持同版本多 recipe revision 并存，必须用后缀版本号区分）。
> 本版本与 1.61 配方的唯一差异：`conanfile.py version='1.61.1'`、`conandata.yml`
> 注释同步；其余适配逻辑（configure 参数 / TMPDIR / umask / WEAK 关闭 / patch）
> 逐项沿用 1.61 已验证结论（W0b 历史经验比对通过）。

## 编译环境
- 构建系统: autotools
- 适配日期: 2026-09-27
- 编译器: clang / clang++ (clang 15.0.4, libc++, target aarch64-unknown-linux-ohos)
- 目标: os=OHOS, arch=armv8 (aarch64), Release
- conan: 2.29.1（OHOS 适配版）；profile: `ci/conan/profiles/ohos-aarch64`
- 状态: built（本地 `conan create` EXIT=0，test_package 鸿蒙特有测试 PASS）

## 源码
- URL: `https://gnupg.org/ftp/gcrypt/libgpg-error/libgpg-error-1.61.tar.bz2`（官方源，R39）
- sha256: `7a85413f2bc354f4f8aa832b718af122e48965e9e0eb9012ee659c13c6385c93`（实测一致）
- 说明：1.61 为 1.55 的同族版本升级（接口无变化）；1.61.1 复用同一 tarball。

## 编译步骤
1. `get()` 下载官方 tarball 并校验 sha256
2. `export_sources()` 导出 `patches/`（**必需**，否则 `apply_conandata_patches` 找不到文件）
3. `apply_conandata_patches()` 应用 config.guess / config.sub 的 HarmonyOS patch
4. `TMPDIR` 指向 conan build 目录；configure 内 `umask 077` → `022`
5. configure：`--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl --disable-nls --disable-doc --disable-tests --disable-static`
6. 关闭 `USE_POSIX_THREADS_WEAK`（musl 误判修正）
7. `make -j1` → `install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess` 不识别 OHOS → "unable to guess system type" | ① OHOS 不在 autoconf 支持列表；② 设备 HMDFS 上 mktemp 探针写 `dummy.c` 报 Permission denied | 显式 `--build/--host=aarch64-unknown-linux-musl` 跳过 config.guess（并保留 config.guess patch 作双保险）|
| 2 | `config.sub` 不识别 OHOS | 同上 | patch config.sub（`ohos*` / `linux-ohos*` 分支）|
| 3 | conftest / 临时文件写入失败 | 设备默认 `TMPDIR` 在 HMDFS 上 | `TMPDIR` 指向 conan build 目录 |
| 4 | 临时文件权限异常 | configure 内 `umask 077` 在 HMDFS 上行为异常 | 改为 `umask 022` |
| 5 | 编译报 `use of undeclared identifier 'pthread_cancel'` | gnulib `threadlib.m4` 的 `gl_pthread_in_glibc` 只认 glibc，把 musl 误判为需 `-lpthread` → 定义 `USE_POSIX_THREADS_WEAK`；musl 的 pthread 在 libc 内，weak 引用不成立 | 去掉 `config.h` 的 `USE_POSIX_THREADS_WEAK` 定义（回退 `use_pthread_p()=(1)`）|
| 6 | `FileNotFoundError: .../s/patches/0001-...patch` | `patches/` 未经 `export_sources()` 导出 | 加 `export_sources()` + `export_conandata_patches(self)`（同 npth 1.8）|

## 为什么必须 build == host（重要）

libgpg-error 的 `src/lock-obj-pub.*.h` 是**平台相关的锁尺寸定义**。以 cross 模式构建时，
configure 会走 `force_use_syscfg=yes`（套用**预置**的 glibc 头）；而 `--build == --host`
时为原生模式，会实际运行 `gen-lock-obj.sh` 探针，按**设备真实 musl** 的 pthread 尺寸生成。

若误用 glibc 预置头，后续 gnupg 链在运行期会因 pthread 锁尺寸不匹配而出现难排查的问题 ——
这是本方案选择 `--build/--host=...musl`（而非仅 patch config.guess）的核心原因。

## 上游测试三步法清点（R51）

### ① 清点
- 测试目录：`tests/`（tests/Makefile.am 的 `TESTS`，14 项）+
  `src/`（src/Makefile 的 `TESTS = gpg-error-config-test.sh`，1 项）。
- 测试框架：automake `make check`（无 ctest/pytest）。
- 测试用例数：**15 项**（14 + 1）。

### ② 实际运行方式（2026-09-27 在本设备真实执行）
```bash
# 1.61 源码解压后，configure **不加 --disable-tests**
cd build-tests
export TMPDIR=<可写目录>          # 设备默认 TMPDIR 在 HMDFS 上写临时文件失败
export CC=/data/service/hnp/bin/clang
../libgpg-error-1.61/configure --build=aarch64-unknown-linux-musl \
    --host=aarch64-unknown-linux-musl \
    --disable-nls --disable-doc --disable-static   # 注意：不加 --disable-tests
# configure 内 umask 077→022（HMDFS 上 confXXXXXX 创建会 Permission denied）
make -j1
make check
```
> 注：`make` 首次会因 `USE_POSIX_THREADS_WEAK`（musl 误判）编译报错，与配方
> build() 相同处理——注释掉 `config.h` 的 `#define USE_POSIX_THREADS_WEAK 1` 后
> 重新 `make`（手动复现与配方 build() 逻辑一致）。

### ③ N/N′ 实测结果
**15 项中 14 项通过（93.3%）**，`make check` 输出 `1 of 14 tests failed`（tests/ 目录内
14 项；src/ 的 gpg-error-config-test.sh 独立 PASS）。逐项明细见 `reports/test-report.md`。

### 崩溃点说明（t-argparse）
- **崩溃点**：`src/sysutils.c` 的 `_gpgrt_getusername()`（:683）在 `:715` 调用
  `pwd = getpwuid (getuid());`；`getpwuid()` 返回 NULL → `src/argparse.c:693`
  `assure_username()` 报 `error getting current user's name: System error w/o errno`
  并返回 `ARGPARSE_PERMISSION_ERROR` → `tests/etc/t-argparse.conf` 的 `${_user}`
  展开（:11/:18/:57/:78）期望输出不一致。
- **崩溃原因**（本设备实测）：进程 UID **20020101** 不在 `/etc/passwd`；
  - `python3 -c "import pwd; pwd.getpwuid(20020101)"` → `KeyError: getpwuid(): uid not found: 20020101`
  - `os.access('/etc/passwd', os.W_OK)` → `False`；`/etc/passwd` 为 root 属主 `0644`
  - `sudo -n true` → `exit 1`（无免密 sudo）
  - `_gpgrt_getusername()` 非 W32 分支**无环境变量回退**（源码通读确认：不读
    `$USER`/`$LOGNAME`，仅有 `getpwuid` 一路）
- **结论**：属**测试宿主 passwd 数据库缺失的环境限制，非库缺陷**；与 1.61 基线
  结论完全一致，无 `--disable-tests` 之外的可修复路径（passwd 不可写、无 sudo、
  代码无 env 回退，测试环境变量 `$USER=100` 亦不被该函数读取）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/gpg-error` | 错误码查询工具 |
| `bin/gpgrt-config` | 配置工具 |
| `include/gpg-error.h`, `include/gpgrt.h` | 头文件 |
| `lib/libgpg-error.so*` | 共享库（`libgpg-error.so.0.42.1`）|
| `lib/pkgconfig/gpg-error.pc` | pkg-config |
| `share/aclocal/gpg-error.m4`, `gpgrt.m4` | autoconf 宏 |

## 测试

- **test_package（鸿蒙特有，R34 反空壳）**：`dlopen` 真实加载 `libgpg-error.so`，
  `dlsym` 解析并**实际调用**被测库 API：
  - `gpg_strerror(GPG_ERR_NO_ERROR)` → `'Success'`
  - `gpg_strsource(GPG_ERR_SOURCE_ANY)` → `'Unspecified source'`
  - `gpg_error_check_version(NULL)`（gpgrt/gpg-error 版本 API）→ `'1.61'`
  - 实测输出：
    ```
    libgpg-error: gpg_strerror(0)='Success' ok
    libgpg-error: gpg_strsource(ANY)='Unspecified source' ok
    libgpg-error: gpg_error_check_version()='1.61' ok
    ```
- 上游测试：`--disable-tests` 关闭（出包配方），但上游测试已在 R51 三步法下
  单独真实运行并逐项记录（见 `reports/test-report.md`）。

## 下游

libgpg-error 是 **gnupg 链基座**：`gnupg` / `libassuan` / `libksba` / `npth` / `pinentry`
均依赖它；也是 apt 满血依赖链（签名验证 `gpgv`）的上游基座。
---

**编译结束**: 2026-09-28 19:14
**最终状态**: built
