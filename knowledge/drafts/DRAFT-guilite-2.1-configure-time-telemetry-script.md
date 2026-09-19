# DRAFT: 构建期遥测/统计上报脚本应补丁移除（configure-time telemetry）

> 来源：guilite 2.1 适配（executor pc4-11，2026-09-19）
> 状态：DRAFT — 待评审转正（对应 `.kv` 同 stem：`DRAFT-guilite-2.1-configure-time-telemetry-script.kv`）

## 问题

上游为统计构建信息，在 CMakeLists.txt configure 期用 `execute_process` 无条件调用遥测脚本。
GuiLite 的 `.sync.sh` 会上传构建信息到 PowerBI，并 `curl ipinfo.io` 采集地域信息。

## 根因

1. configure 期发起外联网络请求：沙箱/CI 环境可能失败、挂起，或泄露构建信息。
2. 依赖 `/tmp` 写临时文件（`/tmp/ip_info.tmp` 等）：只读/HMDFS `/tmp` 下构建失败。
3. 该调用与构建产物、测试完全无关，删除不影响任何功能。

## 方案

补丁删除 CMakeLists.txt 中的 `execute_process(COMMAND ${CMAKE_SOURCE_DIR}/.sync.sh GuiLite)`，
或降级为本地幂等、无外联实现。删除后复跑 `conan create` 验证构建与测试不受影响。

## 验证

guilite 2.1：补丁 `0001-CMakeLists.txt.patch` 删除 `.sync.sh` 调用；
`conan-verify` G2（`conan create` + test_package 消费者测试）通过，构建无外联依赖。

## 适用边界 / 反例

- 适用：库构建系统在 configure/build 期无条件调用遥测/统计上报脚本，且调用与产物无关。
- 反例：a) 官方授权类上报（许可证检查）不可盲删；b) 遥测调用有功能副作用（如版本探测）时
  需改为本地探测；c) 上游 CI 依赖则降级为幂等本地模式。
- 本库边界：GuiLite `.sync.sh` 仅上传统计 + ipinfo 外联，删除后构建/测试完全不受影响。

## 查重差异

七轴查重（详见 `archives/g/guilite/2.1/reports/knowledge-ledger.md`）：
exact_duplicate=否、causal_duplicate=否、trigger_overlap=无、
solution_overlap=部分（E334 网络后端门禁相近但范围不同）、combination_novelty=是、
boundary_novelty=是、test_migration_novelty=无。知识库无「configure 期遥测移除」既有条目。

## 关系

- `similar_to`: DRAFT-libcec-8.1.7-ohos-no-whoami-buildinfo（构建期非必要外联行为）
- `prerequisite_of`: E276/E103/E293（配方能构建是暴露遥测问题的前提）
- `conflicts_with`: E334（适用范围不同，需注明边界）