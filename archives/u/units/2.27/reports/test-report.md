# units 2.27 测试报告

环境：HarmonyOS PC aarch64 独立 HiShell（uid 20020084），OHOS Clang 15，Conan 2.29.1；Conan host/build profile 使用 `os=OHOS`、`os.version=6.0`、`arch=armv8`、`libc++`。

| 阶段 | 结果 | 证据 |
|---|---|---|
| Conan `conan create` | 通过（rc=0） | `~/ohpc-incoming/verify-two-units-fixed3-20260924/units/conan-create.log` |
| 配方内核心换算 | 通过，`2 m = 200 cm` | 同上 |
| 消费者测试 | 8/8 通过 | `units smoke: 8 assertions passed` |
| 官方 CI | 未执行 | 待 PR 创建后由上游门禁运行 |

测试覆盖长度、质量、时间、面积换算、非法单位拒绝及定义/元素数据文件加载。
