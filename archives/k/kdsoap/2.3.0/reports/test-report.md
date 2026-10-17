# KDSoap 2.3.0 目标平台验证

目标机：HarmonyOS PC aarch64，`10.62.201.39:2222`（动态校园网 IP，仅为本次证据端点）。

| 项目 | 结果 |
| --- | --- |
| 官方源码 | KDAB release 2.3.0，SHA-256 `d2184951145cb768cc30376a10701be13869a164c1272d09f831ba2d195f02de` |
| 依赖 | `qtbase/6.11.1` 已发布版本 |
| W3 冻结事务 | `kdsoap-w3-20261005-r14`，单次 runner，完整 receipt 01–12，validator PASS |
| Conan 创建 | RC 0 |
| 上游 CTest | 54/54 PASS，含 `kdsoap-test_serverlib` |
| 安装包消费者 | 1/1 PASS，真实调用 KDSoap 公共 API |
| 原始日志 | `D:\Projects\harmonyPC\workspace\kdsoap-2.3.0-adaptation-20261005\w3-r14\conan-create.log`；SHA-256 `9ab90000f5649a9b1e819ff9acfcc382bb55623063ad4c2a78ffc28897f9e2bc` |
| 完整清单 | 54 项，`D:\Projects\harmonyPC\workspace\kdsoap-2.3.0-adaptation-20261005\w3-r14\upstream-inventory.txt`；SHA-256 `c012a1433368c8208022b7197a600201feac97fa840ce1d7bad5afb0b4d4f610` |

限制：平台 AI Review 与比赛 worker CI 尚未运行；目标机通过不能替代二者。`serverlib` 的不可读文件夹具在鸿蒙上条件性 XFAIL，不删除其 CTest 项；详见 PR 正文。
