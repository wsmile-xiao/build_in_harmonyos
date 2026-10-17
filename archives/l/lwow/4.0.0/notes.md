# lwow 4.0.0 适配笔记

## 上游测试清点（R51 三步法）

**第一步 清点**：官方 v4.0.0 tag 源码全量枚举，无任何自动化测试套件：
- `find . -type d -iname '*test*'` → 无结果
- `find . -type f \( -iname '*test*' -o -iname '*check*' -o -iname '*spec*' \)` → 无结果
- CMake 无 `add_test`/`enable_testing`/`include(CTest)`；无 gtest/unity/cmocka/doctest/catch2 引用
- CI 工作流（.github/workflows）仅 release 发布 + PlatformIO 发布，无 test job
- 枚举证据：`reports/upstream-test-enum.log`（SHA-256 `9e2fc4d8efacf65d3e7d1ace85d010f791ecb8514a34e40b64dbe1905e2d53e5`）

**第二步 运行**：无可运行入口（0/0），如实记录，未伪造占位符。

**第三步 回填**：`source_declared_total=0` / `configured_executable_total=0` / `executed_passed_total=0`。
全量通过率 0/0（无上游测试）。库功能验证由 test_package + tests/ohos_lwow_test.c + tests/consumer/lwow_consumer.c 承担。

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-23
- 编译器: clang/clang++ (OHOS aarch64)
- 状态: built

## 编译步骤

1. 下载官方 v4.0.0 源码（GitHub release tag），SHA-256 核验
2. 库为纯 C（LwOW — Lightweight OneWire），`lwow/` 子目录是独立库 CMake 工程
3. conanfile.py：`cmake.configure(build_script_folder="lwow")` 编出 `liblwow.a` + `liblwow_devices.a`
4. 上游 library.cmake 无 install 规则 → package() 手动打包；CMakeDeps 只生成 `lwow::lwow` 单一 target
5. test_package：模拟 1-Wire 总线，调 lwow_init/lwow_reset/lwow_write_byte_ex/lwow_read_byte_ex/lwow_crc，PASSED
6. 鸿蒙专项测试 tests/ohos_lwow_test.c：位级总线模拟驱动，覆盖搜索 ROM + DS18B20 温度读取，PASSED (25.0625°C)
7. 消费者用例 tests/consumer/lwow_consumer.c：温度巡检业务（枚举+逐台读温+平均），PASSED

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conandata.yml 带版本嵌套报 TypeError | conan 2.x `conan_data["sources"]` 需扁平结构 | 改为扁平 `sources: {url, sha256}` + `patches: {}` |
| 2 | `CMake.configure(source_dir=)` 报错 | CMake 工具不支持 source_dir 参数 | 改 `build_script_folder="lwow"` |
| 3 | 包内缺 liblwow_devices.a 报 "Library not found" | cmake_layout 下 self.build_folder 已是 build/Release，原路径 `build/Release/lwow` 不存在 | 候选路径探测（含 self.build_folder 本身） |
| 4 | test_package 引用 `lwow::lwow_devices` 报 target not found | 多库包 CMakeDeps 仅生成单一包 target | 只链接 `lwow::lwow`（内含两个 .a） |
| 5 | ctest 无 test target | 测试未注册 | CMakeLists 加 enable_testing + add_test |
| 6 | 简单回显驱动无法完成 ROM 搜索 | 搜索需按位响应 ROM 位与补位 | 实现状态机模拟驱动（PHASE_SEARCH/PHASE_SCRATCH） |
| 7 | presence 模拟值 0x00 被判定无设备 | reset 检查 `byt==0 || byt==0xF0` | 回 0x55 |

## 源码修改

无（纯配方适配）。

## 知识沉淀

- 已申请路径 B（知识库扩展）：lwow 适配沉淀了「无 install 规则的 CMake 子工程库的 conan 打包」与「CMakeDeps 多库单 target」经验，见 knowledge 候选台账（reports/knowledge-candidate-ledger.md）。
---

**编译结束**: 2026-09-23 04:38
**最终状态**: built
