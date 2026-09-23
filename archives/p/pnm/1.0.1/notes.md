# pnm 1.0.1 HarmonyOS PC 适配记录

- 上游：`https://github.com/ToruNiina/pnm`，tag `v1.0.1`，SHA256 `50ec55e28e3223950bf69470cf7d6dcdc4240858595d2bf0418734d6ba0a2fe6`
- 类型：C++11 header-only；无三方依赖，仅标准库。
- 适配方式：安装 `pnm.hpp` 到 `include/`，安装 `LICENSE` 到 `licenses/`；导出 CMake target `pnm::pnm`。
- 补丁：无。

## 测试证据

- 上游测试：`test_pixels`、`test_image`、`test_io` 共 10 个 Catch2 `TEST_CASE`，1263 个断言，3/3 测试程序通过。
- 上游首次配置因 CMake 4.1 移除低于 3.5 的兼容策略失败；使用官方提供的 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容选项后通过。未修改上游测试。
- 消费者测试：`test_package` 1/1，通过 `pnm::write/read` 验证 RGB PPM 二进制图像往返，4 个断言。
- Conan 验证：`conan create ... -s:h compiler.libcxx=libc++ -s:b compiler.libcxx=libc++ --build=missing` 通过。

## 环境说明

设备默认 profile 的 `compiler.libcxx=libstdc++` 会使 clang 报 `invalid library name in argument '-stdlib=libstdc++'`；该工具链环境实际使用 libc++，因此验证命令显式覆盖为 `libc++`。这属于设备 profile 配置与工具链不一致，不是 pnm 源码问题。

路径 B：本次为标准 header-only 打包与消费者验证，未发现可跨库复用的诊断模式或组合方案，暂不申报知识库扩展，也不创建路径 B Issue。

## 结束记录

- 最终状态：built
- 结束条件：Conan create、上游测试、消费者测试均已完成；PR 正文按积分赛事模板填充。
---

**编译结束**: 2026-09-04 00:53
**最终状态**: built
