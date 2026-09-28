# Clang-only 目标上游 CMake 覆盖编译器与非法 C 标准值

## 触发场景

在 HarmonyOS PC AArch64 上构建 `ud/1.1.0`。目标有 Clang 15、CMake 和
Conan，但没有 `gcc`。上游官方标签 `v1.1.0` 的 CMake 文件在
`project(ud)` 之后硬编码 `set(CMAKE_C_COMPILER gcc)`。

## 现象与根因

即使显式传入 `-DCMAKE_C_COMPILER=clang`，配置阶段报告 Clang，构建阶段
仍执行不存在的 `gcc`，报 `make: gcc: No such file or directory`。
去掉编译器覆盖后，`set(TARGET ud PROPERTY C_STANDARD 18)` 既不是设置
目标属性的正确语法，标准值 `18` 也导致该 CMake 版本报
`C_STANDARD is set to invalid value '18'`。

## 处理与验证

配方仅在取得官方源码后移除 GCC 覆盖，将标准设置为
`set(CMAKE_C_STANDARD 17)`。C17 与 C18 指同一 2018 ISO C 修订版；
`main.c` 完全不修改。CMake/Clang 暂存文件放到应用私有可写 `TMPDIR`。
目标机以 `conan create -pr:h ohos-aarch64 -pr:b ohos-aarch64` 隔离构建
成功，安装包消费者的 9/9 项确定性检查通过。

上游 CMake 未注册 CTest 用例，其 GitHub 工作流仅运行一次不校验输出的
`./ud` 冒烟调用。新增检查覆盖 UTC epoch、负 UNIX day、20000 号日、
三种日期格式、版本、帮助和无效参数。官方标签归档 SHA-256 为
`994459ac0b69db6fab913e1f38f92cb02fef26693cdcf15bcd28899010ff5f2f`；
真机最终日志 SHA-256 为
`3f6d57e7e1968ef2faebae778e28048beb5a7b32ef47c813b5eabb24b36b9e49`。

## 边界

本条关于上游 CMake 尊重显式编译器选择的诊断可复用；私有 `TMPDIR`
问题已有其他知识条目，不在此重复计分。最终真机验证使用与官方归档
同哈希的本地 `file://` 副本，因为真机到 GitHub 的 HTTPS 连接超时；
提交配方保持官方 URL。是否独立入库、路径 B 等级、积分和答辩规则
由维护者判定。
