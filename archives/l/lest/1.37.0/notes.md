# lest 1.37.0 适配记录

## W0/W0b

- 任务语言和源码均为 C++，构建系统为 CMake，无 Conan 依赖；官方 tarball SHA-256：`ff31a4ded6589387d029d7d10ec1d787420adf1ccdb2ec96ab2da92b4d5993a7`。

## 构建与测试

- 上游 CMake 的 `LEST_BUILD_EXAMPLE` 默认开启，但 example 目录包含演示失败断言，完整 CTest 的 28 个目标中有 15 个按设计失败。
- recipe 关闭演示 example，仅运行标记为 `unittest` 的 9 个上游单元测试目标；设备实测 9/9 通过。
- test_package 真实调用 `lest::run`、`CASE` 和 `EXPECT`，2 个消费者测试通过。

## 路径判断

- 本任务走路径 A。关闭教学示例属于上游已有构建选项，不形成新的跨库知识草稿。

## 对话记录

### 对话 #1（2026-09-03）

- 首轮驱动已成功构建全部目标，但安装 staging 绝对路径被框架误判；独立 CTest 核对确认 unit-test 标签为 9/9，失败目标均来自故意展示失败行为的 examples。

## 结束

最终状态: built
