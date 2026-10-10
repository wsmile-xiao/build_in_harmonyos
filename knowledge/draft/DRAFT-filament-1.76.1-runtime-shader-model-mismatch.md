# DRAFT-filament-1.76.1-runtime-shader-model-mismatch

> Contributor: ohos-farm | Status: Draft | Updated: 2026-09-17
> Source: filament 1.76.1 HarmonyOS PC 适配（PR #10480）
> 领域：runtime|shader|build-configuration|conan

## 背景

Filament 1.76.1 在 HarmonyOS PC 上完成 pass 1（7 个宿主工具）、pass 2（100%）、打包与 test_package 链接后，二进制在**首次运行**时 core dump（exit 139）。构建、链接、打包三段全绿，问题只在运行期暴露。

## 错误签名

```text
The material 'Filament Default Material' was not built for desktop.
Compiled material contains shader models 0x2.
timeout: the monitored command dumped core            (exit 139)
```

## 根因

位掩码 `0x2` 是 bit1，即 MOBILE。而该设备上每一个驱动都返回 `ShaderModel::DESKTOP`。构建期 `MATC_TARGET` 跟随 `FILAMENT_LINUX_IS_MOBILE`，只产出了移动变体。`MaterialDefinition::create()` 比对失败返回 nullptr，`Engine::create()` 解引用崩溃。

## 触发条件

构建期着色器目标与运行期驱动上报的着色器模型来自两个独立配置，且二者不一致。

## 修复方案

让构建期同时产出两个着色器族（`MATC_OPT_FLAGS = "-p;all"`），而**不是**关掉那个承载链接行为的移动开关。注意 CMake list 分隔符必须是 `;`。

## 验证

见 `.kv`：CMake 管道、argv 假程序、产物体积三层对照，外加端到端 14 项运行期断言。
