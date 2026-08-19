# DRAFT-cargo-test-no-doctest：OHOS Rust 工具链缺 rustdoc → cargo test 加 --lib --bins --tests 排除 doctest（保留单元+集成测试）

> Contributor: librsvg-2.62.3 适配 | Status: Draft | Updated: 2026-08-14
> Source: archives/l/librsvg/2.62.3（round-9 CI，上游测试启用，交付 commit 0ca0b722ea）

## 现象

OHOS harmonybrew 裁剪的 Rust 工具链缺 rustdoc 组件。cargo test 默认会编译并运行
doctest，doctest 编译依赖 rustdoc，缺失即失败。

## 证据：设备端 rustdoc 存在性探针（2026-08-14 实测）

```
$ ls ~/.harmonybrew/bin/rustdoc
ls: /storage/Users/currentUser/.harmonybrew/bin/rustdoc: No such file or directory

$ ls ~/.harmonybrew/Cellar/rust/*/bin/rustdoc
ls: /storage/Users/currentUser/.harmonybrew/Cellar/rust/*/bin/rustdoc: No such file or directory

$ ~/.harmonybrew/bin/rustdoc --version
sh: /storage/Users/currentUser/.harmonybrew/bin/rustdoc: inaccessible or not found
```

结论：harmonybrew Rust 工具链确实不含 rustdoc 组件（三个路径均未找到）。
"缺 rustdoc" 最初为 Builder 断言，现经设备端 rustdoc 存在性探针实证升级为日志实证。

## 与现有知识的关系

- knowledge/graph 共 323 条，grep `rustdoc` / `doctest` / `cargo test` /
  `--tests` 于 knowledge/docs/references 均无结果——本主题无覆盖。
- 既有 E180 仅覆盖 Rust 工具链可用性（工具链能否运行），**不覆盖组件缺口**
  （工具链是否含 rustdoc）；本主题是 E180 的下游细分，建议 promote 时互链。
- 本草稿为"一类问题"（跨库可复用）：任意在 OHOS 上用 harmonybrew Rust 工具链
  运行 cargo test、上游 Rust 库含 doctest 的 Conan 适配都可能命中。

## 方案

精确排除 doctest：cargo test 默认编译并运行 doctest（依赖 rustdoc，OHOS harmonybrew
工具链缺该组件）。目标选择上注意：`--tests` **仅选择集成测试目标**，会一并丢弃
lib/bin 的 `#[cfg(test)]` 单元测试——若需保留单元测试必须加 `--lib --bins`。
推荐完整命令 `cargo test --lib --bins --tests`：保留 lib 与 bin 单元测试 + 集成测试，
doctest 不在其中（天然排除），单元与集成测试全部真实运行；在 conandata
patch_description + MANIFEST.yml 双重声明豁免原因（TEST_QUALITY_SPEC §3.3）。

## 验证证据

librsvg 2.62.3 在 HarmonyOS aarch64 真机单包 CI：

- round-16 PASS：patch 0003 在 meson/cargo_wrapper.py 的 test 分支加
  `--lib --bins --tests`，排除 doctest（因 OHOS rust 工具链缺 rustdoc 组件），
  lib/bin 单元测试与集成测试全部保留并真实运行；CI exit 0，上游 3 套件真实运行
  （C API tests OK、Rust tests (rsvg) OK、Rust tests (librsvg) OK）。

## 禁止做法

- 不要不声明地跳过整组测试——违反 TEST_QUALITY_SPEC §3.3（须逐条声明豁免原因）。
- 不要伪造 rustdoc 输出——掩盖平台工具链缺口。
- 不要用 `cargo test --skip doctest`——`--skip` 只跳过运行不跳过编译，仍会尝试
  编译 doctest，无法规避 rustdoc 缺失。
