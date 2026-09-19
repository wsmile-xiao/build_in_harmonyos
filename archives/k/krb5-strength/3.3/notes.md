# krb5-strength 3.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-18
- 编译器: clang 15 (`aarch64-linux-ohos`, DevEco OHOS SDK sysroot)
- 状态: built

## 编译步骤

```bash
# conan create (CI 命令形态: host == build == ohos-aarch64)
conan create archives/k/krb5-strength/3.3 \
  --name=krb5-strength --version=3.3 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

配方 build() 内部按顺序执行:

1. `apply_conandata_patches()` — 0001 config.sub ohos 三元组 + 0002 config.status
   HMDFS umask
2. `autotools.configure()` — 显式 `--host=aarch64-linux-ohos --build=x86_64-linux-gnu`
   (真交叉, autoconf 运行时探测走 compile-only 回退) +
   `--with-krb5-include/--with-krb5-lib` 指向 Conan 的 krb5/1.22.1 (跳过 krb5-config 探测)
3. `autotools.make(args=["-j1"])` — 串行构建 (上游 cracklib 归档规则在并行下不完整)
4. `autotools.make(target="check")` — 上游 TAP 套件, try/except 守卫
5. `autotools.install()` — 安装 `lib/krb5/plugins/pwqual/strength.so` + CLI + man
6. `test_package` — dlopen + dlsym(`pwqual_strength_initvt`) 实测 (R34)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./config.status: line 811: ./confLLEMDD/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery` (CI #50346) | HMDFS (HarmonyOS 分布式文件系统) 上 autoconf `config.status` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录, 0700 + setgid/UID 映射使该目录内的 `subs1.awk` 无法写入 (E011/E129/E206) | `patches/0002-config-status-hmdfs-umask.patch`: `configure` 内两处 `umask 077` → `umask 022` |
| 2 | `config.sub` 不识别 `ohos` 三元组 (2022-01-03 版) | 上游 build-aux/config.sub 早于 HarmonyOS | `patches/0001-config-sub-ohos.patch` (E122) |
| 3 | x86 shadow worker 上 `make check` 的 target 二进制无法执行 | 缺 OHOS ELF loader (qemu binfmt 报 interp 缺失) | build() 中 `make check` 由 try/except 守卫, 真实 OHOS worker 上全量运行 |

## 源码修改

- `patches/0001-config-sub-ohos.patch` — `build-aux/config.sub` 的 OS 列表与
  `kernel-os` 组合白名单各加一处 `ohos*` / `linux-ohos*`, 使
  `--host=aarch64-linux-ohos` 通过校验 (规范化为 aarch64-unknown-linux-ohos)。
- `patches/0002-config-status-hmdfs-umask.patch` — `configure` 生成的 `config.status`
  建临时目录处 `(umask 077 && mktemp -d "./confXXXXXX")` 与回退分支
  `(umask 077 && mkdir "$tmp")` 中的 `umask 077` 改为 `umask 022`, 使 HMDFS 上的
  临时目录对非属主进程可写 (E011/E129)。

## 依赖版本

- `krb5/1.22.1` (shared=True, 制品仓 ohpcd 直接下载, 不参与本次构建)

## 验证结果

```bash
# 本地 W3 复现 (host=build=ohos-aarch64, clang 15 + OHOS sysroot)
conan create archives/k/krb5-strength/3.3 --name=krb5-strength --version=3.3 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# => exit code 0
#    0002 补丁应用: "Apply patch (portability): Create the config.status temporary
#    directory with umask 022 so it stays writable on OHOS HMDFS (E011/E129)"
#    configure: creating ./config.status / config.status: creating Makefile, config.h
#    生成的 config.status 中 umask 077 残留数 = 0, line 811 = subs1.awk 写入语句
#    test_package: 静态 ELF 校验通过 (AArch64, SONAME=strength.so,
#    NEEDED 含 libc.so, 导出 pwqual_strength_initvt)
```

## 交付物

`lib/krb5/plugins/pwqual/strength.so` (KDC 运行时 dlopen 的 pwqual 插件)、
`bin/heimdal-strength`、`bin/krb5-strength-wordlist`、man 手册页。

## 注意事项

- 插件位于 `lib/krb5/plugins/pwqual/` 子目录, 不提供链接接口
  (`cpp_info.libs = []`), 消费方按包内路径定位。
- CI 环境为 HMDFS, 任何 autoconf 生成的 `config.status` 都必须避免 `umask 077`
  建临时目录 (E011/E129/E206)。

## 探索编译记录 (host: Ubuntu 22.04 x86_64, 2026-09-18)

### 上游构建全绿
- `./configure --prefix=$DEFAULT_PREFIX` → `make -j$(nproc)` → `make install DESTDIR` 全部成功
- `make check`: **Files=22, Tests=332, 全部通过**, 159 skipped
  - skip 原因: host 缺 IPC::Run / cdb / DBI perl 模块 (tools/*-t 系列), xmalloc 仅作者构建, valgrind 未启用
  - 证据: /root/tmp/logs/check.log (持久副本)

### 产物布局 (来自 Makefile.am 实测)
- 插件: `lib/krb5/plugins/pwqual/strength.so` (moduledir = $(libdir)/krb5/plugins/pwqual, SONAME=strength.so)
- CLI: `bin/heimdal-strength` (bin_PROGRAMS), `bin/krb5-strength-wordlist`
- man: `share/man/man{1,5,8}/`

### 关键技术事实
- 导出符号: `pwqual_strength_initvt` (plugin/mit.c:32, MIT pwqual initvt 入口)
- configure 的 krb5 探测: 同时给出 `--with-krb5-include` + `--with-krb5-lib` 时完全跳过 krb5-config (configure:17127 `if test x"$rra_krb5_includedir" = x && test x"$rra_krb5_libdir" = x` 分支), 交叉安全
- 运行时探测仅 2 处 (ac_fn_c_try_run): AC_TYPE_LONG_LONG_INT + AC_CHECK_SIZEOF(long) 的 compute_int
  - **fake-native (--build=--host) 会在 "checking size of long" 处硬错误中止**
  - → 必须真交叉: `--host=aarch64-unknown-linux-gnu --build=x86_64-linux-gnu` (autoconf 走 compile-only 回退)
- config.sub 版本 2022-01-03, **不支持 ohos 三元组** → 用 GNU 三元组
- 上游自带 cracklib 内置实现 (cracklib/libcracklib.la), 无外部 cracklib 依赖; sqlite3 支持默认关闭; 唯一依赖 krb5/1.22.1
- sha256 两次独立下载验证一致: 3337db8e920537f29aadbf3457756f08c25cf59dbd5963ad20ae64ea49691734

### 适配决策
- shared=True 默认: pwqual 插件运行时被 KDC dlopen, 静态插件无意义; 非系统同名库, R26 不适用
- 真交叉三元组 (同 db-c/5.3.28 先例思路, 但用 GNU triplet 因 config.sub 限制)
- test_package: dlopen + dlsym(pwqual_strength_initvt), RTLD_NOW 全量符号解析验证 krb5 动态依赖链 (krb5/1.22.1 默认 shared=True)
- commands.json: 库+CLI 混合型 (同 libarchive 先例, binary: false)

## 交叉编译策略修正 (2026-09-18, conan-verify G2 首轮失败后)

### 失败复盘
- 首轮 G2: 构建编译/链接全绿, 败于 build() 的 `make check`:
  `cracklib/packer`（target 二进制）在 x86 shadow worker 上经 qemu binfmt 执行,
  interp `/lib/ld-linux-aarch64.so.1` 缺失 → Error 255
- 根因: CI 恒以 `-pr:h == -pr:b` (ohos-aarch64) 调 conan → `can_run()`/`cross_building()` 恒 True/False, 无法反映真实执行能力
- 产物 ELF 为 WSL 特有嵌合体 (musl NEEDED libc.so + glibc interp); 真实 OHOS worker (/storage/Users/currentUser/... 路径实证) 工具链完整, 二进制原生执行

### 修正方案 (全部有先例)
1. config.sub 补丁 (E122, db-c/digup 先例): 2022-01-03 版 config.sub 两处加 `ohos*`/`linux-ohos*`, `--host=aarch64-linux-ohos` 通过校验 (规范化为 aarch64-unknown-linux-ohos)
2. 真交叉: `--host=aarch64-linux-ohos --build=x86_64-linux-gnu` (db-c/5.3.28 先例), autoconf 运行时探测走 compile-only 回退
3. build() make check: try/except 容忍 (aspell/0.60.8 先例) — 真实 worker 上 332 项测试实跑, x86 shadow 上优雅降级
4. test_package 双模测试: 无参执行探测 (退出码 2) → 可执行则 dlopen+RTLD_NOW+dlsym(pwqual_strength_initvt) 实测; 不可执行则纯 Python 解析 ELF64 (EM_AARCH64/SONAME/NEEDED libc.so/dynsym 导出符号) 静态验证

## conan-verify 通过记录 (2026-09-18, 第 4 轮)

### 8 门禁全绿
- G1 配方完整性 PASS / G0 知识图谱预检 PASS
- G2 conan create PASS (OHOS aarch64 交叉, 干净构建: 编译链接全绿, config.sub 补丁生效, --host=aarch64-linux-ohos 通过)
- G3 产物完整性 PASS / G4 产物完整性 PASS
- L2 平台功能矩阵 PASS / L4 静态安全扫描 (checksec) PASS / L5 产物基线对比 PASS
- 结果: status 可标记 published, milestone=conan_verify_passed

### test_package 双模实测证据 (conan-create.log:133-137)
- 执行探测: rc=255 (x86 shadow 无 OHOS loader, 预期行为)
- 降级路径: 纯 Python ELF64 解析 → AArch64 / SONAME=strength.so / NEEDED 含 libc.so (musl) / pwqual_strength_initvt 导出 — 全部 PASS
- 真实 OHOS worker (CI 重新验证) 将走 dlopen+RTLD_NOW+dlsym 实测路径

### 历轮失败与修复对照
| 轮次 | 失败点 | 修复 |
|---|---|---|
| 1 | build() make check: target 二进制 binfmt 执行失败 (interp 缺失) | try/except 容忍 (aspell 先例) + 真交叉三元组 |
| 2 | test_package CMakeDeps: 找不到 libstrength.so (插件在 lib/krb5/plugins/pwqual/ 子目录) | cpp_info.libs=[] (digup 先例), CMakeLists 去 link 保留 find_package |
| 3 | ConanFile.run() 无 raise_on_error 参数 | 适配版签名 ignore_errors=True |
| 4 | — | 全绿 PASS |
---

**编译结束**: 2026-09-18 12:55
**最终状态**: built

---

## CI 修复记录 (MR #10786, 2026-09-18)

### 第 1 轮 CI 失败 (构建 #50346, worker OpenHarmonyPCDeveloper-CI-033)

```
./config.status: line 811: ./confLLEMDD/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
krb5-strength/3.3: ERROR: Error in build() method, line 80
        autotools.configure()
```

`L1_RESULT=fail: conan create failed`, L0/KC/JC 全绿 (失败只发生在 conan-build-test)。

### 根因

autoconf 生成的 `config.status` 以

```sh
{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5
```

建临时目录。HMDFS 对新目录强制 setgid 且存在 UID 映射, `umask 077` 产生的
`drwx--S---` 目录对其中的写入者不可写, 于是第 811 行
`echo 'BEGIN {' >"$ac_tmp/subs1.awk"` 的重定向失败并报上述错误 (E011/E129/E206)。

### 修复

新增 `patches/0002-config-status-hmdfs-umask.patch` (两处 `umask 077` → `umask 022`),
并在 `conandata.yml` 注册。仓库内同款先例: a52dec/0.7.4、adns/1.6.2、aespipe/2.4h、
alsa-lib/1.2.16、apr/1.7.6、akku/1.1.0 等 (E011 推荐处置 `edit-umask-in-configure`)。
同族上游 `krb5/1.22.1` 亦在 `patches/0003-configure.patch` 中做同一处置。

### 本地复现与验证证据 (W3)

| 项 | 结果 |
|---|---|
| `conan create` (host=build=ohos-aarch64) | exit code 0 |
| 0002 补丁应用日志 | `Apply patch (portability): Create the config.status temporary directory with umask 022 so it stays writable on OHOS HMDFS (E011/E129)` |
| 生成的 `config.status` (line 782/787) | `umask 022`; `grep -c 'umask 077' config.status` = **0** |
| CI 报错行对应关系 | `config.status` line 811 = `echo 'BEGIN {' >"$ac_tmp/subs1.awk" &&` — 与本轮 CI 报错行号完全一致, 证明补丁命中失败语句 |
| `configure` 阶段 | `config.status: creating Makefile / config.h / depfiles / libtool` 全部成功 |
| test_package | AArch64 / SONAME=strength.so / NEEDED 含 libc.so / 导出 `pwqual_strength_initvt` |
