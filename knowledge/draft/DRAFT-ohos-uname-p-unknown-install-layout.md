# DRAFT-ohos-uname-p-unknown-install-layout

> Contributor: ohos-farm | Status: Draft | Updated: 2026-09-17
> Source: filament 1.76.1 HarmonyOS PC 适配（PR #10480）
> 领域：platform-limitation|packaging|conan|cmake

## 背景

Filament 1.76.1 在 HarmonyOS PC 上打包成功后，`test_package` 的 CMake configure 报`no static archives found under .../p/lib`。检查发现包是建出来了，但 `lib/` 下 0 个 `.a`，34 个归档全在 `lib/unknown/`。

## 错误签名

```text
CMake Error at CMakeLists.txt:29 (message):
  no static archives found under .../p/b/filam.../p/lib
```

## 根因

(1) `uname -p` 在该内核上返回字面量 `unknown`，`CMAKE_HOST_SYSTEM_PROCESSOR` 因此为 `unknown`，上游的 `DIST_ARCH` 回退把安装子目录定成 `lib/unknown/`；
(2) 配方未声明 `cpp_info.libdirs`，默认 `lib` 与实际布局不符。两者叠加使包'建得出来但消费不了'。

## 触发条件

安装子目录派生自宿主处理器 + 配方未同步声明实际 libdir。

## 修复方案

钉住 `DIST_ARCH`、用复数的 `cpp_info.libdirs` 声明实际位置、在 `package()` 加断言。

## 验证

见 `.kv`：赋值实验（证明 `libdir` 只读）、真实 package_info 的 CMakeDeps 产物、端到端布局。
