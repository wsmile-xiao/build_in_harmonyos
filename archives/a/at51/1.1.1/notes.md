# at51 1.1.1 HarmonyOS PC 适配说明

## 软件说明

at51 是使用 Rust 编写的 8051 固件逆向分析命令行工具，提供 stat、base、libfind、kinit 四个子命令。

## HarmonyOS PC 适配

- 使用 Cargo / Rust 构建
- 使用上游 Cargo.lock，通过 `--locked` 固定依赖版本
- 使用 clang 作为 OHOS/Linux 上的 Rust linker
- 将 Cargo target 和临时目录设置为构建目录下的可写路径
- 保持上游源码不变
- 无源码 Patch

## 上游测试

上游 Cargo 测试共计 38 项，分布在：

- `src/kinit.rs`
- `src/libfind/aslink3.rs`
- `src/libfind/mod.rs`
- `src/libfind/omf51.rs`

OHOS aarch64 真机验证结果：

- 38 项通过
- 0 项失败
- 0 项忽略

执行命令：

```sh
cargo test --release --locked --no-fail-fast --bins --tests
```

## test_package

新增 test_package 对最终 Conan 制品进行 CLI 冒烟验证：

- `at51 --help`
- `at51 stat --help`
- `at51 base --help`
- `at51 kinit --help`
- `at51 libfind --help`

共 5 项验证。

## 真机 CI 结果

- 端口：旧端口 56267
- Run 目录：`/storage/Users/currentUser/ohos-test-runs/codex-a-1.1.1-at51-1.1.1-oldport-r1-20260814-conan-20260815-222107-41019`
- `cargo build --release --locked`：通过
- `cargo test --release --locked --no-fail-fast --bins --tests`：38/38 通过
- `conan create`：通过
- `test_package`：5/5 通过
- CI 门禁：L0/L1/L2/L4/L5 全部通过
