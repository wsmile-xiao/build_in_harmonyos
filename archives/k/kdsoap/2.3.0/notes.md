# KDSoap 2.3.0 HarmonyOS PC 适配记录

- 官方源码 SHA-256：`d2184951145cb768cc30376a10701be13869a164c1272d09f831ba2d195f02de`；Conan 依赖为已发布的 `qtbase/6.11.1`。
- 上游 CMake 测试开关 `KDSoap_TESTS=ON`，真实注册 54 项；`test_package/MANIFEST.yml` 与 r14 原始 CTest Start 1..54 一致。
- `0001` 用 Qt 的 `QT_NO_SSL` 宏保护 `QSslError` 完整类型；`0002` 在权限位不生效的文件系统上用明确打不开的路径验证 HTTP 403，而不再用 `QEXPECT_FAIL` 掩盖响应；`0003` 保持生产代码原有本地时间语义，用通用 Qt 本地时间参考值及显式 `Qt::LocalTime` 断言校验空时区；`0004` 所有平台统一使用有界慢响应夹具，保留响应内容、连接数和线程数断言。补丁中不再使用 `__OHOS__` 分支。
- 目标机 r14 属于修复前候选，曾得到 `conan create` RC 0、上游 54/54、安装后消费者 1/1、释放/后释放/validator PASS；它不为本轮 Review 修复背书。本轮独立重验见 r17。r14 原始日志 SHA-256：`9ab90000f5649a9b1e819ff9acfcc382bb55623063ad4c2a78ffc28897f9e2bc`。
- r11 曾因并发测试在 5 个有效响应后只观察到 4 个活跃服务对象而 53/54；这属于测试前提的时序敏感性，不以跳过原断言或重跑掩盖。可复用模式提炼为 `knowledge/drafts/E891-draft-KD14`。
- r15 真机在源码应用阶段失败：`0002` 在测试文件前部增加 4 行后，Conan `patch-ng` 对 `0004` 的原始行号不做模糊偏移，导致 hunk 不匹配。r15 已终态失败并完成 release/postrelease；后续候选须从干净官方源码用 `patch-ng` 精确顺序重放，不能把本地 `git apply` 成功当作等价验证。
- r16 真机补丁应用与编译通过，上游测试 53/54：`groupwise_wsdl::testStringBaseType` 发现将空时区从 `Qt::LocalTime` 改为 `QTimeZone::systemTimeZone()` 会改变 `QDateTime` 规格并破坏序列化往返等价。r16 已终态失败并完成 release/postrelease；修复撤销生产代码变更，保留明确的跨平台本地时间断言。
- r17 使用当前四个补丁在干净官方源码上通过 `patch-ng 1.19.1` 精确顺序重放；目标机冻结事务 `kdsoap-w3-20261009-r17`：`conan create` RC 0、上游 CTest 54/54（含 Groupwise、serverlib、kddatetime）、安装后消费者 1/1、release/postrelease 和冻结 validator PASS。原始 `conan-create.log` SHA-256：`2889a6f70752837470f44be16159295324c0717c6f85fe31c712784bccb4283b`。这是当前 Review 修复的目标验证，不代表平台 PR CI 或新 HEAD 的 AI Review 已完成。
- 本轮路径复核：HD1=false（只使用 Qt/KDSoap 公共接口）；HD2=false（标准 Conan/CMake 与目标机现成 Clang，未使用私有工具链）；HD3=false（不改 SOAP/线程池架构，只修正测试夹具与头文件顺序）；HD4=false（仅依赖已发布的 `qtbase/6.11.1`，54 项上游测试约 8 秒，虽全量编译较慢但无额外大型依赖矩阵）。保持路径 B／`【知识库扩展】`，以 r17 的配方、测试及原始日志为证据。
- PR #14822 的新 HEAD 仍需平台 AI Review 与 CI 验证。`kdsoap-ws-discovery-client/0.4.0` 必须等本包正式发布，不能把本地通过当作已发布依赖。
