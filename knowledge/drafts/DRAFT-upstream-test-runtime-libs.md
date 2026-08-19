# DRAFT-upstream-test-runtime-libs：测试制品运行时 .so 可达按来源拆分注入

> Contributor: librsvg-2.62.3 适配 | Status: Draft | Updated: 2026-08-14
> Source: archives/l/librsvg/2.62.3（round-5→round-9 CI，上游测试启用链，交付 commit 0ca0b722ea）

## 现象

OHOS 上启用上游测试时（librsvg 2.62.3 round-5 起），测试二进制运行期需可达大量
传递依赖 .so，但不同测试制品的运行时依赖解析机制不同，导致两类失败：

1. **C API 测试缺传递依赖 libdirs**（round-7 pixman）：meson 编译的 C API 测试二进制
   RUNPATH 只含直接依赖 libdirs，不含 pixman 等传递依赖，运行期报
   `cannot open shared object file: libpixman-1.so.0`。
2. **cargo test 编译期 lld 被 LD_LIBRARY_PATH 污染**：若全局注入 LD_LIBRARY_PATH
   试图一并解决 C API 测试问题，会污染 cargo test 编译期调用的 lld——lld 自带
   libxml2（与系统 libxml2 版本/ABI 不一致），被 LD_LIBRARY_PATH 遮蔽后产生链接期
   错误。
3. **Conan 2.x `ConanFile.run()` env 参数限制**：env 参数只接受环境文件名列表
   （source_env 语义），不接受 dict 形式的 `{KEY: VALUE}`，因此运行期环境注入须用
   `os.environ` 临时设置 + `finally` 恢复，不能依赖 `self.run(..., env={...})`。

## 与现有知识的关系

- knowledge/graph 共 323 条，grep `LD_LIBRARY_PATH` / `RUSTFLAGS` / `rpath` /
  `RUNPATH` / `pixman` / `lld` 于 knowledge/docs/references 均无结果——本主题无覆盖。
- 既有 E186 覆盖 cargo 本体运行时 musl ldso namespace，**机制与方向不同**
  （E186 用 patchelf 修 cargo 本体；本主题是测试运行期注入拆分），互补不重叠。
- 既有 DRAFT-staticlib-transitive-libs 覆盖链接期传递依赖收集，**机制相关但阶段不同**
  （链接期 vs 运行期），不合并，建议互链。
- 本草稿为"一类问题"（跨库可复用）：任意在 OHOS 上启用上游测试、测试制品依赖大量
  传递动态库、且混用 meson 编译二进制与 cargo test 的 Conan 适配都可能命中。

## 方案

按测试制品来源拆分运行时 .so 可达注入策略：

1. **C API 测试（meson 编译二进制）**：运行期单独注入 `LD_LIBRARY_PATH`，含全部依赖
   libdirs（含 pixman 等传递依赖），通过 `os.environ` 临时设置 + `finally` 恢复。
2. **Rust 测试（cargo test）**：用 `RUSTFLAGS` rpath
   （`-C link-arg=-Wl,-rpath,<libdir>`）在链接期烙入 RUNPATH，避免 `LD_LIBRARY_PATH`
   污染编译期 lld。
3. **二者隔离**，不混用同一环境变量策略；`ConanFile.run()` env 参数限制用
   `os.environ` + `finally` 规避。

## 验证证据

librsvg 2.62.3 在 HarmonyOS aarch64 真机单包 CI：

- round-7 FAIL：C API tests 报 `cannot open shared object file: libpixman-1.so.0`
  （meson 编译二进制 RUNPATH 缺传递依赖 libdirs）。
- round-8 FAIL：尝试用 patchelf 改测试二进制 RUNPATH，破坏 OHOS 代码签名
  （`WriteCodeSignBlock error`），重签失败，二进制不可用（见
  DRAFT-patchelf-breaks-ohos-signing）。
- round-9 PASS：采用拆分注入策略——C API 测试用 `LD_LIBRARY_PATH`（含全部依赖
  libdirs 含 pixman），Rust 测试用 `RUSTFLAGS rpath`（RUNPATH 指向依赖 libdirs，
  避免 LD_LIBRARY_PATH 污染构建期 lld）；CI exit 0，上游 3 套件真实运行
  （C API tests OK 8.03s、Rust tests (librsvg) OK 502.37s、
  Rust tests (rsvg) OK 1086.16s）。

## 禁止做法

- 不要对 meson 编译的测试二进制用 patchelf 改 RUNPATH——会破坏 OHOS 代码签名
  （见 DRAFT-patchelf-breaks-ohos-signing）。
- 不要用全局 LD_LIBRARY_PATH 同时喂 C API 测试与 cargo test——会污染 cargo test
  编译期 lld（lld 自带 libxml2 被遮蔽），产生链接期错误。
- 不要依赖 `self.run(..., env={...})` 注入运行期环境——Conan 2.x 的 env 参数只接受
  环境文件名列表，不接受 dict；须用 `os.environ` + `finally` 规避。
