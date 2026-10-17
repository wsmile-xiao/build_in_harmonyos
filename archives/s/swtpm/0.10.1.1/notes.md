# swtpm 0.10.1.1 适配笔记

> **版本说明**：conan 引用版本 `0.10.1.1` 表示**基于上游 0.10.1 的 OHOS 适配轮次**
> （本仓惯例，如 gnupg `2.4.9.1`）。源码 URL 仍指向上游 `v0.10.1.tar.gz`，
> 交付产物自报版本亦为 `0.10.1`（上游版本号不因适配轮次改变）。

## 编译环境

- 构建系统: autotools（源码为 git archive 快照，无预生成 configure）
- 编译日期: 2026-09-20
- 编译器: clang / clang++
- 目标三元组: aarch64-unknown-linux-ohos（由 config.guess 自动识别）
- 状态: built

## 编译步骤

```sh
# 1. 取源码（git archive tag 快照，无 configure）
#    https://github.com/stefanberger/swtpm/archive/refs/tags/v0.10.1.tar.gz
#    sha256 f8da11cadfed27e26d26c5f58a7b8f2d14d684e691927348906b5891f525c684

# 2. 应用 conandata 补丁（0001：移除 configure.ac 中后置的 -Werror）
# 3. 生成构建系统（tool_requires 提供 automake/1.18 + libtool/2.5.4）
autoreconf --install --force

# 4. 关键：补 config.guess 识别 HarmonyOS（autoreconf 复制来的版本不认）
#    由配方 _patch_config_guess() 插入 *:HarmonyOS:*:* 分支

# 5. 从生成的 configure 中移除 umask 077（E114）
# 6. 配置与构建（不传 --build/--host，R1）
./configure --enable-static --disable-shared \
            --without-gnutls --without-seccomp --without-cuse --without-selinux \
            --disable-tests --disable-hardening
make -j1        # E074：HMDFS jobserver fifo EPERM，须串行
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan export` 立即失败：`Patch file does not exist: patches/0001-remove-Werror-for-clang-compat.patch` | 该 patch 在 main 上**从未提交**（`git ls-tree` 查证 `patches/` 目录不存在），而 `conandata.yml` 已引用 | 从上游 `configure.ac` 精确定位 `-Werror` 行，用 `diff -u` 生成补丁文件 |
| 2 | `configure: error: cannot guess build type; you must specify one` | autoreconf 复制的 automake/1.18 `config.guess` 无 HarmonyOS 分支（`grep -c ohos` = 0）；`uname -s` 返回 HarmonyOS | 在 `build()` 内 autoreconf **之后**补 `config.guess`（此文件构建期才生成，conandata 补丁打不到） |
| 3 | 原配方用 `--build/--host=aarch64-unknown-linux-ohos` | 违反 R1（禁止三元组）；且 CI 上传 `--build=<gnu triplet>` 会触发 `C compiler cannot create executables` | 移除两个参数，改由 `config.guess` 识别（`config.sub` 实测已接受 ohos，无需处理） |
| 4 | `-Wno-error` 无法压制上游的 `-Werror` | 上游 `configure.ac` 把 `-Werror` 追加在 `CFLAGS` **末尾**，位置后于工具链注入的 `-Wno-error` | 补丁 0001 从该行移除 `-Werror` |
| 5 | `umask 077` 使 config.status 无法建临时目录（E114） | HMDFS 强制目录 setgid | 从生成的 `configure` 中移除 `umask 077` |
| 6 | `make -j` 并行失败（E074） | HMDFS jobserver fifo `EPERM` | `make -j1` |
| 7 | OHOS 缺 seccomp / cuse / gnutls / selinux | 系统无对应内核接口或库 | `--without-seccomp --without-cuse --without-gnutls --without-selinux` |
| 8 | 上游测试需 `socat`，OHOS 无 | 测试脚本依赖外部工具 | `--disable-tests`（如实申报测试未跑，不掩盖） |

## 源码修改

`patches/0001-remove-Werror-for-clang-compat.patch`

```diff
--- a/configure.ac
+++ b/configure.ac
@@ -542,7 +542,7 @@
 AC_SUBST([TSS_GROUP])

 CFLAGS="$CFLAGS -Wreturn-type -Wsign-compare -Wswitch-enum"
-CFLAGS="$CFLAGS -Wmissing-prototypes -Wall -Werror"
+CFLAGS="$CFLAGS -Wmissing-prototypes -Wall"
 CFLAGS="$CFLAGS -Wformat -Wformat-security -Wshadow"
```

仅移除 `-Werror`，保留其余告警级别；不触及其他上游代码。

> `config.guess` 的修补在配方 `build()` 内完成（不落为 conandata 补丁），
> 原因是该文件由 autoreconf 在构建期生成，`source()` 阶段尚不存在。

## 依赖版本

| 依赖 | 版本 | 角色 |
|------|------|------|
| libtpms | 0.10.2 | TPM 1.2/2.0 仿真核心 |
| glib | 2.84.0 | 基础运行时 |
| json-glib | 1.6.6 | JSON 状态序列化 |
| libtasn1 | 4.21.0 | ASN.1 编码 |
| openssl | 3.5.6 | 加密原语 |
| gmp | 6.3.0 | 大数运算 |
| automake | 1.18 | autoreconf（tool_requires） |
| libtool | 2.5.4 | autoreconf（tool_requires） |

## 验证结果

```bash
# 端到端
conan create archives/s/swtpm/0.10.1 --version=0.10.1
# → EXIT=0

# 交付产物可执行性（gnupg 的消费方式：${SWTPM} socket --tpm2 ...）
swtpm --version
```

（详细命令与实测输出见 PR 描述「验证结果」章节。）

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/swtpm` | TPM 模拟器守护进程（gnupg tpm2dtests 消费此文件） |
| `bin/swtpm_setup` | TPM 状态初始化工具 |
| `bin/swtpm_ioctl` | 控制接口工具 |
| `bin/swtpm_bios` | BIOS 初始化辅助 |
| `bin/swtpm_localca` | 本地 CA 工具 |
| `bin/swtpm_cert` | 证书生成工具 |

## 注意事项

- **运行期走 TCP**：`--server type=tcp,port=2321 --ctrl type=tcp,port=2322`
  可规避 OHOS 对 AF_UNIX 路径名 socket 的限制。
- **`--tpmstate dir=`** 需指向可写目录（写入 `NVChip` 等状态文件）。
- **`config.guess` 修补位置不可前移**：放在 `source()` 会因文件不存在而失败。
- 上游测试未执行：上游测试依赖 `socat`（OHOS 无），故 `--disable-tests`。
  已如实申报，未以 skip/xfail 掩盖。

---

**编译结束**: 2026-09-20
**最终状态**: built
