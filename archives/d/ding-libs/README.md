# ding-libs

ding-libs 是 SSSD 项目提供的一组可复用 C 工具库，包含 `dhash` 动态哈希表和 `ini_config` INI 配置解析/校验库。

## 功能

- 提供动态哈希表、字符串/整数键值操作和迭代 API。
- 提供 INI 文件解析、配置对象、规则校验与序列化 API。
- 通过 Conan 组件分别消费 `dhash` 与 `ini_config`。

## OpenHarmony 适配

- 在 HarmonyOS PC arm64（`os=OHOS`、`arch=armv8`）上使用 clang/LLVM 15 原生构建。
- 适配 GNU Autotools 对 `aarch64-unknown-linux-ohos` 的识别。
- 针对 HMDFS 临时目录权限、文件模式归一化、`open_memstream` 大小发布和 musl regex 诊断差异提供可移植补丁。
- 上游 20 项 Check 测试及 Conan public-API test package 已在设备端通过。

## 依赖

库本身不增加 Conan 运行时依赖；上游 Check 测试使用 `check/0.15.2` test requirement。

## 参考资料

- 上游仓库：https://github.com/SSSD/ding-libs
- 0.7.0 Conan 配方：[`0.7.0/`](0.7.0/)
