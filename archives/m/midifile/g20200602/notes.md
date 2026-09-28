# midifile g20200602 适配笔记

## 软件信息

- 上游: <https://github.com/craigsapp/midifile>（Craig Stuart Sapp / CCRMA；
  Standard MIDI File 解析/创建 C++11 库）
- 版本: g20200602（快照提交 d1c2139083d1386db55860d29eac14b11a95a9c8，
  2020-02-08，为 2020-06-02 快照日前最后提交）
- 任务: ohpcd（领取时无人认领、无 PR 记录、仓库未收录）

## 编译环境

- 真机: 10.195.180.238（隔离 job `device-b/midifile-kb-20260920`）
- 构建系统: cmake（仅构建库目标）；状态: built

## 上游测试清点（R51 第 1 步）

| 清点项 | 结果 | 依据 |
|---|---|---|
| tests/ 目录 | 不存在 | 解包清单 |
| ctest 注册 | 无 | CMakeLists 无 add_test/enable_testing |
| tools/ | 32 个示例 CLI（演示用，非断言） | CMakeLists add_executable 列表 |
| 上游测试 | **0 个** | 消费者 SMF 往返为唯一验证 |

## 适配要点

- 上游 cmake_minimum_required(2.8) → CMAKE_POLICY_VERSION_MINIMUM=3.5（E103/E321）
- 上游无 install 规则 → 配方手工安装 include/*.h + libmidifile.a
- 默认构建 32 个工具 → 仅构建 midifile 库目标

## 验证结果（真机实测后回填）

- conan create: 退出码 0
- 消费者: **6/6 断言通过**（ctest 1/1 + 直接执行）

## 注意事项

- PR 前缀【知识库扩展】；分支 feat/midifile-g20200602
