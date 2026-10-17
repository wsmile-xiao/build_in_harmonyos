# kcodecs 6.26.0.1 notes

## Scope

KDE Frameworks 6.26.0 baseline of kcodecs (string/text codecs library,
`libKF6Codecs.so`), delivered as `kcodecs/6.26.0.1` for the `kio/6.26.0.1`
dependency closure. Depends on qtbase/6.11.1 (Qt6Core), ecm/6.26.0 (ECM build
tool) and libiconv/1.17 (legacy charset fallback).

## 6.26.0 → 6.26.0.1（本版差异）

本版配方与制品仓中已发布的 `kcodecs/6.26.0` **内容一致**，差异仅为版本号字符串
（`conanfile.py` 的 `version`、`conandata.yml` 的 patches 键、`manifest.yaml`）：

| 项目 | 6.26.0（已发布） | 6.26.0.1（本版） |
|---|---|---|
| 上游源码 URL / SHA256 | kcodecs-6.26.0.tar.xz / `ee1fe3bd…bcb4` | 相同 |
| patches 0001-0005 | 相同（逐字节一致） | 相同 |
| requires / tool_requires | qtbase/6.11.1、libiconv/1.17、ecm/6.26.0 | 相同 |
| DT_SONAME 注入（`-Wl,-soname,`） | 已含（6.26.0 基线配方） | 相同 |

**为何递增版本号**：`.1` 的动因来自 **`kio/6.26.0.1` 依赖闭包**——闭包内下游配方
（`kcompletion/6.26.0.1`、`kconfigwidgets/6.18.0.1`）精确 `self.requires("kcodecs/6.26.0.1")`，
而 cnb.cool 制品仓不支持同版本多 recipe revision 并存（R37），故需独立 `.1` revision 供下游锁定。
**核验边界（勿误读）**：上述引用配方目前仅存在于**本地闭包工作区**（`.wt-kio`，`kio/6.26.0.1` 分支），
**尚未合入 main**——在本 PR 的基线（main + 本包）上检索不到任何 `requires("kcodecs/6.26.0.1")`，
现网 `kcompletion/6.26.0` 使用的是 `kcodecs/6.26.0`。因此本 PR 属该闭包的**前置发布**（依赖注册顺序：
先有 `kcodecs/6.26.0.1` 制品，闭包配方的精确引用才可解析）。本包不含库侧行为改动，属闭包版本对齐；
本版已在 OHOS 上重新全量编译验证（见 Verification）。

## Adaptations

Same adaptation set as the 6.18.0/6.26.0 recipes:

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during the Conan build;
  `BUILD_FUZZERS=OFF` keeps oss-fuzz helper targets out.
- `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG = -Wl,-soname,` injected on OHOS:
  native builds stay in CMake's `Generic` platform module (no
  `Platform/HarmonyOS`), which has no soname rule, so `VERSION`/`SOVERSION`
  would not reach the linker and `libKF6Codecs.so` would lack `DT_SONAME`.
- `ecm_install_po_files_as_qm(poqm)` disabled (patch 0001): the Qt Linguist
  tools component is not part of the OHOS qtbase package.
- libiconv fallback (patches 0002/0003): qtbase on OHOS is built without ICU,
  so `QStringDecoder` cannot decode some RFC2047 legacy charsets. The patches
  add an iconv-based decode fallback (`decodeWithIconv`) wired in via
  `KCODECS_ICONV_LIBRARY` when libiconv is present.
- ECM_MODULE_PATH set manually and `conan_cmakedeps_paths.cmake` written by the
  recipe because the CMakeDeps-generated ECMConfig.cmake does not propagate
  ECM_MODULE_PATH and qtbase uses `cmake_find_mode=none`.
- `/system/lib64` prepended to LD_LIBRARY_PATH for cmake/ctest runtime so the
  compatible `libc++_shared.so` wins over the sandbox one (kconfig 6.26.0 /
  bluez-qt 6.28.0 precedent).

## 上游测试适配（6.26.0 引入的两个新问题）

1. `kencodingproberunittest` (new upstream test) does not link `KF6::Codecs`,
   so `target_compile_features(KF6Codecs PUBLIC cxx_std_20)` is not propagated
   and it compiles with `-std=c++17`, breaking `std::span` usage in
   `nsCodingStateMachine.h`. Patch 0004 adds an explicit
   `target_compile_features(kencodingproberunittest PRIVATE cxx_std_20)`
   (CMake-only change, no test source touched).
2. `kcharsets.cpp` uses `std::string_view <=> std::string_view` which the OHOS
   libc++ (clang 15 toolchain) does not implement. Patch 0005 replaces it with
   `compare() <=> 0` (built-in integer spaceship), preserving the
   `std::strong_ordering` return type.
3. `parseEncodedWord`'s `maybeCharset` is a `QByteArrayView`; the iconv-fallback
   `conversionCharset` needs an explicit `QByteArray(maybeCharset)` conversion
   (patch 0003).

## Verification

- Upstream tarball SHA256 verified:
  `ee1fe3bd8bcd93a84d44186a5fc50395b6bf43dd2bf8972338a7aad72aa0bcb4`.
- All five patches apply cleanly to the unpacked 6.26.0 source.
- OHOS full (forced, non-cached) `conan create` verification on 2026-09-30:
  `conan create . -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build="kcodecs/*"`
  → rc=0，日志 `tmpdir/kcodecs-create2.log`（531 行，含全部编译与测试输出）。
  - Upstream CTest (inside conan create, BUILD_TESTING=ON): 6/6 passed
    (`base45test`, `codectest`, `kemailaddresstest`, `kcharsetstest`,
    `kencodingproberunittest`, `kencodingprobertest`).
    `rfc2047test` is **excluded at run time** (`ctest -E "^rfc2047test$"`): its
    "working-QP" rows expect `QStringEncoder("ISO-8859-15")` which the ICU-less
    OHOS qtbase cannot provide, so KCodecs falls back to the System codec
    ("Locale") and the expected encoded-word differs. The test still compiles
    (binary linked); environment limitation, not a kcodecs regression
    (kconfig 6.26.0 exclusion-list precedent).
  - Conan `test_package`: 1/1 passed — base64 round trip, quoted-printable
    round trip and RFC2047 decode all verified (3 assertions, real API calls).
  - Package created: id `546f25c40e62843f04e563647cb09d4d09d8b48c`;
    artifacts `lib/libKF6Codecs.so{,.6,.6.26.0}` + `include/KF6/KCodecs/*`
    + `lib/cmake/KF6Codecs`.

---

**编译结束**: 2026-09-30 14:38
**最终状态**: built

## 对话记录

### 对话 #1 — 2026-09-30

- 目标：交付 `kcodecs/6.26.0.1`，作为 `kio/6.26.0.1` 依赖闭包的一员（PR 前缀【依赖项】），
  提交到分支 `feat/kcodecs-6.26.0.1`。
- 配方来源与差异核对：`.1` 与已合入 main 的 `kcodecs/6.26.0` 逐字节比对，差异仅为版本号
  字符串（`conanfile.py` 的 `version`、`conandata.yml` 的 patches 键），5 个补丁内容完全一致。
- 闭包引用核对：`.1` 的动因来自 `kio/6.26.0.1` 闭包（下游 `kcompletion/6.26.0.1`、
  `kconfigwidgets/6.18.0.1` 精确 require `kcodecs/6.26.0.1`）；**本分支内无该引用**
  （`kcompletion/6.26.0` 使用 `kcodecs/6.26.0`），引用存在于尚未提交的闭包工作区
  → 本 PR 为闭包前置发布（依赖注册顺序，R37），PR 正文已如实说明该边界。
- 本地验证：第一次 `conan create` 命中本地缓存（177 行日志，无编译输出），**改
  `--build="kcodecs/*"` 强制全量重编译**取得真实证据 → rc=0、上游 CTest 6/6、
  `test_package` 1/1、包 id `546f25c40e62843f04e563647cb09d4d09d8b48c`。
- `rfc2047test` 运行期排除原因确认：其 working-QP 行需要 ICU 提供的 `ISO-8859-15` 编码器，
  OHOS qtbase 无 ICU（沿用 kconfig 6.26.0 排除清单先例），用例本身仍参与编译。
- finish（W3）通过：`.ci-result.json` `exit_code=0`（integrity_hash `56b1b45ebbaca771`，
  日志 SHA256 `1b8f70a8…98de`），W2 原子性检查确认仅含配方变更（13 文件）。
- W4 独立审计（首轮）判 `fail`（P1=1）：`.1` 的升版理由在本分支不可核实（引用的
  `kcompletion/6.26.0.1` 不在 main）。经用户决策采用"如实表述 + 重审"路径：文档改为显式说明
  "引用配方位于未合入的闭包工作区、本 PR 为前置发布"，其余机制项（R34/R8/R33/R38/R39/R51）
  审计全绿。

---

**编译结束**: 2026-09-30 14:38
**最终状态**: built
