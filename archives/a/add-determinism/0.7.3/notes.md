# add-determinism 0.7.3 HarmonyOS PC 适配说明

## 软件说明

add-determinism 是使用 Rust 编写的确定性构建辅助工具，主要提供 add-det 和 linkdupes 两个命令行程序。

## HarmonyOS PC 适配

- 使用 Cargo / Rust 构建
- 使用 HarmonyOS PC 可用 Rust 工具链
- 使用 clang 作为 Rust linker
- 将测试临时目录设置为 /data/storage/el2/base/cache/add-determinism-rust-tmp
- 避免 HarmonyOS 文件系统权限语义差异影响普通测试
- 不修改上游业务源码
- 无源码 Patch

## 上游测试

上游 Cargo 测试共计 880 项。

HarmonyOS PC 实际结果：

- 863 项通过
- 17 项因平台文件系统能力差异过滤
- 0 项实际失败

17 项过滤测试均依赖 HarmonyOS 当前文件系统不支持或受限的能力，主要包括：

- hardlink
- creation time / birth time

同时使用 --lib --bins --tests 执行 Cargo 测试，避免依赖当前环境中不可用的 rustdoc doctest。

## test_package

新增 test_package 对最终 Conan 制品进行 CLI 冒烟验证：

- add-det --version
- add-det --help
- linkdupes --help

共 3 项验证。

## 验证

执行：

python3 scripts/ohc-run.py conan-verify add-determinism 0.7.3

结果：

- G1 PASS
- G2 PASS
- G3 PASS
- G4 产物完整性检查完成
- L2/L4/L5 检查完成
- 配方验证通过
