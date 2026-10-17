# midifile g20200602 知识证据报告

- 真机：10.195.180.238，隔离 job `device-b/midifile-kb-20260920`；2026-09-20
- 环境：clang 15.0.4（aarch64-unknown-ohos）、Conan 2.29.1、SDK cmake 3.28.2

## 适配要点（全部真机实证）

1. **上游 cmake_minimum_required(2.8)**：CMake 4.x 拒绝 <3.5 → 配方 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（E103/E321 既有知识复用，非新知识）
2. **上游无 install 规则 + 默认构建 32 个示例 CLI**：配方仅构建 `midifile` 库目标（`cmake.build(target=...)`），手工安装 include/*.h + libmidifile.a
3. **消费者测试两处设备适配**：
   - 快照版本类在 `smf::` 命名空间内（新版移除了命名空间——快照版必须 `using namespace smf`）
   - 真机 `/tmp` 只读 → 测试临时文件用相对路径（cwd 可写）
   - `addTrack(2)` 语义：默认 1 轨 + 2 = **3 轨**（非 2），往返断言按 3

## EVID 矩阵

| EVID | 类型 | 结果 |
|---|---|---|
| EVID-01 | target-executed | conan create 退出码 0 |
| EVID-02 | target-executed | ctest 1/1 Passed；直接执行 `test_midifile: OK (SMF write/read roundtrip + time analysis)`，6/6 断言（写/读成功、3 轨、3 note-on、音高 60、ontime 0.0s） |

## 测试统计

上游 0（清点：无 tests/、无 ctest 注册、tools/ 为 32 个示例）；消费者 6/6。

## 影子 CI
【待回填】
