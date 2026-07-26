# flang-ohos 20.1.0 编译笔记（HarmonyOS PC · LLVM Flang）

## 定位
- 设备/NDK 不带 Fortran 编译器 → 本包提供 LLVM Flang（`bin/flang`），供含 Fortran 的库
  （openblas 的 LAPACK、scipy 等）在真机 `conan create` 时 `tool_requires("flang-ohos/20.1.0")`。

## 关键适配
- **真机原生编**（不交叉）：不设 `CMAKE_SYSTEM_NAME`，裸 cmake + 设备 hnp clang；config.guess stub
  输出 `aarch64-unknown-linux-ohos`；造 `Platform/HarmonyOS.cmake=include(Platform/Linux)`（同 llvm recipe）。
- `LLVM_ENABLE_PROJECTS="mlir;clang;flang"`（flang 依赖 mlir + clangDriver）；`AArch64`；dylib 瘦身。
- 20.1.0 的 Fortran 运行时是 in-tree `flang/runtime`（目标 `FortranRuntime`/`FortranDecimal`），内建 `.mod`
  随之生成到 `build/include/flang`。
- 打包最小运行集：`bin/flang` + `libLLVM/libMLIR/libclang-cpp.so` + `libFortran{Runtime,Decimal,Common}.a`
  + 13 个内建模块。`.so`/`bin/flang` 均 binary-sign-tool 自签。

## 本地打包例外（同 llvm）
- 全量编 mlir+clang+flang 真机约 **73 分钟**，**超 CI 硬超时 45 分钟** → CI 必 fail、不产二进制。
- 二进制走「真机编好 → `conan cache save` → 手动 `conan upload`」（已上传 openharmonypcdeveloper-conan，
  package_id `fc3eeb02…`）。本 recipe 留档 + 可复现构建方法；消费方 `conan install` 直接取已发布二进制。

## 消费
```bash
# 作 tool 依赖（含 Fortran 的库 recipe 里）：
def build_requirements(self):
    self.tool_requires("flang-ohos/20.1.0")
# build() 里 FC = <flang-ohos 包>/bin/flang，链接 Fortran 喂 <包>/lib/libFortranRuntime.a
```

## 状态
built（真机原生编 + 真机跑通：编 Fortran→执行结果正确；被 openblas/0.3.34 用于编 LAPACK 已验证）。
