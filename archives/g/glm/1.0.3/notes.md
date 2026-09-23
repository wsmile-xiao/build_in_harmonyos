# GLM 1.0.3 适配笔记

## 源码与配方

- 官方 release：`https://github.com/g-truc/glm/releases/tag/1.0.3`
- 源码归档：`glm-1.0.3.zip`
- SHA-256：`1c0a0fced9b0d87c7b7bc94e40be490cff6d4c83c25db8488d8f33754e7fdeb2`
- 构建系统：CMake；包类型：header-library；第三方依赖：无

## 适配决策

上游安装入口生成 `glmConfig.cmake` 并导出 `glm::glm` INTERFACE target，
不生成运行库。配方因此保持头文件和 CMake metadata 的安装布局，清空
`cpp_info.libs`/`libdirs`/`bindirs`，并在 OHOS profile 下绑定 Linux/aarch64
目标信息。`source()` 按版本键读取 `conandata.yml`，确保 Conan 2 的版本化
源声明传给 `get()` 的是单一 `url`/`sha256` 映射。

## 验证结果

- 官方源 fresh 构建：当前任务根内 378/378 个目标完成，CTest 189/189
  （100%）通过；测试日志 SHA-256 为
  `1ded6b4c16348a84251f80a25481171659130eb655c8536d52b3cec09e36b537`。
- post-W3 Conan OHOS profile：包创建及 AArch64 消费者 2/2 编译链接通过，
  日志 SHA-256 为
  `23232cc44aac202b49ea439180e39ed825a8c951d7446fb1d9b5f430fd8ee3eb`。
- W3 `glm-1.0.3-w3-r005` 在 `10.62.150.125:8022` 完成一次 native
  self-sign 和唯一 launch。目标 RC0，状态断言 4/4、消费者 1/1，stdout
  为 `glm consumer PASS version 1.0.3`，stderr 为 0 bytes；十段 receipt
  hash-chain、readback、release 和最终 `REMOTE_ROOT=ABSENT` 均通过。
- r002/r003 都在 transfer 前因远端根创建失败终止，`launch_count=0`；r004
  的目标执行虽为 RC0，但冻结 host readback 合同失败，未计作 W3 PASS，且
  已清理。不同 run 的结果未拼接到 r005。
- 平台 CI、发布和提审状态必须以各自任务证据回读，不从本地或 W3 结果推导。

**编译收尾**：本地 Conan、上游全量测试与目标 W3 已完成，等待
Pre-PR/平台流程。
