# qrencode 4.1.1.1 适配笔记（上游 4.1.1）

## 适配范围

- 上游仓库: https://github.com/fukuchi/libqrencode
- 上游标签: v4.1.1
- Conan 修订版本: 4.1.1.1（4.1.1 已被制品仓中的不同 recipe 占用）
- 源码 SHA-256: `5385bc1b8c2f20f3b91d258bf8ccc8cf62023935df2d2676b5b67049f31a049c`
- 适配方式: Conan CMake recipe，未修改上游源码，无补丁。

## 配方决策

- `WITH_TESTS=ON`，将上游 CTest 纳入 `build()`，避免只验证安装产物。
- `WITH_TOOLS=OFF`，本 PR 交付库而不是命令行工具，因此不产生 `commands.json` 要求。
- `WITHOUT_PNG=ON`，冻结可选 PNG 后端，避免宿主机依赖探测改变测试分母。
- `shared=False` 为默认值；OHOS shared 选项保留目标机签名入口，默认静态库不依赖签名工具。
- CMake 配置增加 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，兼容当前 CMake 版本对上游旧 minimum 要求的策略检查。

## 本地验证

历史 `build_and_test.sh archives/q/qrencode/4.1.1` 日志仅作为同源码功能基线；修订号迁移后须重新运行 `archives/q/qrencode/4.1.1.1`。

- L0、KC、JC: PASS
- Conan `create` 与 `test_package`: PASS
- 上游 CTest: `3/3` PASS（test_bitstream、test_estimatebit、test_split）
- 消费者测试调用 `QRcode_encodeString`，验证 21x21 矩阵、数据非空并释放对象: PASS
- L1、L5: PASS；L2 按库类型跳过，无 `bin/` 目录
- 历史日志: `archives/q/qrencode/4.1.1/reports/w3-local-ci.log`

## OHOS 真机验证

W3 successor-004 使用唯一事务 `qrencode-4.1.1-w3-20260904-004`，目标 `10.62.150.125:8022`，boot ID `068fec8d-10f6-40f7-93a6-9153e0ad6d33`，属于上游 4.1.1 同源码的历史等价证据，不冒充 4.1.1.1 新事务：

- 上游测试: `12/12` PASS
- 消费者测试: `1/1` PASS
- runner: ABSENT；签名插件回读通过
- release/postrelease: PASS，远端任务根已清理
- 证据目录: `F:\HarmonyPC\miniupnpc-2.3.11-adapt-20260904\w3-successor-20260904-r4`

## 可复用结论

使用 `find_package` 和 option 条件创建测试目标的 CMake 库，必须在配置阶段显式冻结可选后端，再从同一构建树读取 `ctest -N` 并执行完整清单。不要用源码静态文件数替代目标配置后的实际分母；可选依赖缺失时应记录条件测试边界。

## 安全边界

- PNG 输出未纳入默认配方能力；需要 PNG 的消费者必须显式开启 `without_png=False` 并提供完整依赖闭包。
- W3 的 12/12 是 OHOS 目标机冻结事务的证据，不能与其他 run、端点或测试分母拼接。

**编译结束**: 2026-09-04
**最终状态**: built
---

**编译结束**: 2026-09-04 20:39
**最终状态**: built
