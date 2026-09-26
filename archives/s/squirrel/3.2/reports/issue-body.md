## 申请信息
- 申请人：2301_80739235
- 队伍：天天开心
- 日期：2026-09-04
- 软件：squirrel
- 版本：3.2
- 源码：https://github.com/albertodemichelis/squirrel

## 申请原因
为 OpenHarmony PC aarch64 适配 Squirrel 3.2，提供可复用的 C++ 脚本引擎静态库及命令行工具，作为依赖拓扑中的缺失基础组件。该候选已完成官方 v3.2 源码核验、OHOS/arm64 编译、消费者 API 和真机运行验证。

## 知识库查重情况
已检索本地 openharmony-pc 知识库、贡献任务全状态及语义等价任务；未发现 squirrel 3.2 的现有适配记录。本次新增知识聚焦于 Conan shared/static 选项映射、Windows CMake 参数边界、sq_static 命令声明和目标设备自有工具链补齐。

## 可复用说明
本次将沉淀无第三方依赖的 CMake C++ 库在 OHOS/arm64 上进行静态构建、test_package 实质 API 调用、命令行产物登记和真机闭包验证的通用流程，供同类脚本引擎及纯 CMake 依赖复用。

PR：待创建
PR 链接：待创建
当前状态：待创建
