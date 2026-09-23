# libopaque 1.0.1 HarmonyOS PC 移植说明

## 移植范围

- 上游版本：1.0.1（tag v1.0.1，commit dce4732）
- 官方源码：`https://github.com/stef/libopaque/archive/refs/tags/v1.0.1.tar.gz`
- 目标系统：HarmonyOS 6.0 PC（aarch64）
- 构建方式：直接编译上游 C 源码（makefile 方式的手工等价实现）
- Conan 引用：`libopaque/1.0.1`
- 默认产物：静态库（`libopaque.a` + 内嵌依赖的 `liboprf.a`、`libsodium.a`）
- 申请人：yinuoguo；队伍：干

## 依赖策略（W0/R36）

libopaque 硬依赖 libsodium 与 liboprf（`src/opaque.h` 包含
`<sodium.h>` 与 `<oprf/toprf.h>`，见 README "Both must be installed"）：

1. **liboprf 无仓库配方、未发布到制品仓**，不能写 `requires()`（R36/PF4）。
   采用 conandata 第二源码项内嵌 liboprf 0.9.4 官方 tarball（与 Debian
   给 libopaque 1.0.1 配的版本同代：`liboprf-dev (>= 0.3.2)`，
   sid 实际装 0.9.4），只编译核心协议必需的 3 个可移植源文件。
2. **libsodium/1.0.22 未发布到 ohpcd 制品仓**，`requires()` 会触发
   conancenter 影子配方导致真机回退源码构建失败（minisign 0.12 已实证）。
   按 libmacaroons 0.3.0 先例把官方 1.0.22 tarball（与
   archives/l/libsodium/1.0.22 同 URL/SHA）内嵌到私有 prefix 构建，
   产物随本包一起发布，消费者无需任何外部依赖。

liboprf 源码取舍审计（`src/` @ 0.9.4，`grep` 全量 include 与符号引用）：

- 编译：`oprf.c`、`toprf.c`、`utils.c`。`opaque.c` 实际调用的外部符号只有
  `oprf_Blind/Evaluate/Finalize/KeyGen/Unblind` 与
  `toprf_3hashtdh/toprf_thresholdmult`，`toprf.c`/`utils.c` 无 dkg/noise 引用。
- 不编译：`dkg.c`（含 `noise_private.h`）、`tp-dkg.c`、`stp-dkg.c`、
  `mpmult.c`、`toprf-update.c`（含 `<zephyr/kernel.h>`，OHOS 无此头文件）、
  `jni.c`。以上属于阈值 OPAQUE 的 DKG/传输层工具链，不在核心协议内；
  `aux_/kdf_hkdf_sha256.c` 因 sodium >= 1.0.19 不需要（见下）。
- 同理 libopaque 自身只需 `opaque.c`、`common.c`；sodium >= 1.0.19 时
  `-DHAVE_SODIUM_HKDF=1` 使 `aux_/kdf_hkdf_sha512.c` 不被引用。

## 适配内容

1. 上游 `src/makefile` 携带 `-march=native`、sanitizer、pkgconf 探测、
   `uname` 分支等不可移植逻辑，真机无法直接 `make`。配方改为用真机可用
   编译器（PATH 优先探测，`tools.build:compiler_executables` 兜底，R33）
   以最小可移植 flags（`-O2 -std=c99 -fPIC -DHAVE_SODIUM_HKDF=1`）直接编译
   上游源文件并归档，**未修改任何上游源码**，故无 `patches/`。
2. 内嵌 libsodium 走 autotools configure 时复用仓库已验证的三处 HMDFS 修复：
   `configure` 的 `umask 077 → 022`（知识 E114）、`config.guess` 识别
   HarmonyOS、`config.sub` 接受 `linux-ohos`
  （与 archives/l/libsodium/1.0.20 的 0001/0002 等价）；configure 与 make
   全程经 `/bin/sh`（HMBS 注入 SHELL）与 HMBS 独立 TMPDIR 运行，不执行
   profile 中的 hnp bash；`make install` 因 HMDFS 无 chmod/hardlink 会失败，
   改为纯 Python 拷贝归档产物与头文件（libmacaroons 0.3.0 同款）。
3. `opaque.c` 的 `#include <oprf/toprf.h>` 通过构建期纯拷贝的
   `oprf_inc/oprf/*.h` 满足，不用 symlink（HMBS 对 symlink 无保证）。
4. 动态库（`shared=True`）把 opaque+oprf 对象与静态 sodium 打包为单个
   `libopaque.so`；默认静态，`cpp_info.libs = ["opaque", "oprf", "sodium"]`。
5. libopaque 非系统同名库，无需 R26 静态强制；`validate()` 仅接受
   Linux/OHOS（R32 口径）。
6. liboprf 0.9.4 把 `expand_message_xmd()` 更名为 `oprf_expand_message_xmd()`
  （签名一致，见 `src/oprf.h`），而 libopaque 1.0.1 的 `src/opaque.c`
  （`voprf_hash_to_scalar`/`deriveKeyPair`）仍调用旧裸名，导致
   `ld.lld: undefined symbol: expand_message_xmd`。配方以
   `-Dexpand_message_xmd=oprf_expand_message_xmd` 别名兼容，不改上游源码、
   不降级 liboprf；其余 `oprf_*/toprf_*/voprf_hash_to_group` 符号名未变。
7. munit 每例经 `tmpfile()` 缓冲 stderr，而 OHOS libc 的 `tmpfile()`
   硬编码 `/tmp`（musl `src/stdio/tmpfile.c`）且忽略 TMPDIR，真机
   `/tmp` 只读导致 32 例全报 `unable to create buffer for stderr:
   Permission denied (13)`（与知识 E272 同根因，编译期变体）。
   配方在构建期生成 `hmbs_tmpfile_shim.c`（`mkstemp($TMPDIR/…)` +
   `unlink` + `fdopen("w+")`），仅对 munit 对象加
   `-Dtmpfile=hmbs_tmpfile` 并链接该对象；库源码、归档产物不受影响，
   不用 `LD_PRELOAD`，不跳过任何用例。

## 测试范围

- 上游测试（配方 `build()` 内真实编译运行，33 例）：
  - `src/tests/opaque-test.c`（1 个端到端程序：1-step 注册 + 4-step 私有注册，
    各跟一次完整 AKE 与共享密钥比对；断言输出非空且含 `all ok`）；
  - `src/tests/opaque-munit.c` + 内嵌 munit（32 例参数矩阵：
    2 pwdU × 2 idU × 2 idS × 4 注册类型，`--fatal-failures`，
    解析 `N of N tests successful` 行计数）。
  - 未运行 `src/tests/opaque-testvectors.c`（CFRG 向量）：上游仅在存在
    OPRFHOME（liboprf git checkout + 生成的向量头文件）时才编译，
    且结果忽略（`|| true`）；发行 tarball 无此生成文件。详见
    test_package/MANIFEST.yml 的 `upstream_test_audit`。
- 消费者测试（`test_package/test_opaque.c`，10 个检查）：单步注册、完整 AKE、
  共享密钥一致、显式用户认证、export_key 非零、4 步私有注册全链、
  私有记录二次 AKE、错密码负向检查（拒绝或密钥失配均算通过，
  仅"错密码拿到服务器密钥"算失败）。
- 证伪措施：测试输出非空校验；munit 计数与源码审计的 32 例交叉核对，
  不符即警告；负向用例确保 harness 能区分失败（错密码若真拿到相同密钥，
  用例失败而非静默通过）。
- 真机证据：`build()` 与 `test()` 分别打印
  `HMBS_UPSTREAM_TEST_RESULT` / `HMBS_TEST_PACKAGE_RESULT` 合法 JSON；
  上游结果另存入包内 `res/hmbs_upstream.json`，cache-hit 轮由 test_package
  原样重发（cvector 1.0.4.1 先例）。

## 复现命令

HMBS 真机预检通过后（本轮仅完成工作树，尚未验证），复现方式：

```bash
conan create archives/l/libopaque/1.0.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

预期：`conan create` 成功；日志含 `HMBS_UPSTREAM_TEST_RESULT={"status":"passed",...,"discovered":33,...}`
与 `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...,"discovered":10,...}`。

## 已知限制

- 阈值 OPAQUE 的 DKG/noise_xk 传输层、各语言绑定（python/js/lua/go/java/ruby/erlang/php/sasl）
  与 `utils/opaque` 演示 CLI 不打包（纯 C 协议库配方；R38 不适用，无 commands.json）。
- 本轮工作树尚未经过 HMBS 真机预检，`manifest.yaml` 状态为 `pending`，
  数字待证据轮回填；PR 正文草稿见 `.hmbs/pr-body.md`。
