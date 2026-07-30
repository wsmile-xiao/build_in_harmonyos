# flang-ohos 20.1.0 — 鸿蒙 PC conan 制品（LLVM Flang 工具链）

`os=OHOS, arch=armv8`(= aarch64)的 **tool 包**：提供 LLVM Flang（Fortran 前端），供含 Fortran 的库
（openblas/scipy 等）在真机上 `conan create` 时 `tool_requires` 用来编译 Fortran 代码。

## ⚠️ 本地打包（同 llvm）
从源码全量编 LLVM+MLIR+Clang+Flang 真机约 73 分钟，超 CI 45 分钟硬超时 → CI 产不出二进制。
二进制由「真机编好 → conan cache save → 手动 conan upload」提供（已上传制品仓）。本 recipe 留档 + 可复现。

## 前提
所用 conan 的 settings 须含 `os=OHOS`（大写）；stock conan 2 默认不含。推荐 `~/.conan2/settings_user.yml`
的 `os:` 下加 `    OHOS:`，或用 OpenHarmonyPCDeveloper 分发的 conan。

## 消费（作 tool 依赖）
```python
def build_requirements(self):
    self.tool_requires("flang-ohos/20.1.0")

def build(self):
    flang_pkg = self.dependencies.build["flang-ohos"].package_folder
    fc = flang_pkg + "/bin/flang"            # Fortran 编译器
    rt = flang_pkg + "/lib/libFortranRuntime.a"   # 链接 Fortran 时喂它
    # 运行 flang 需 LD_LIBRARY_PATH 含 flang_pkg/lib（libLLVM/libMLIR/libclang-cpp）
    #   及 SDK llvm/lib（lld 的 libxml2.so.16；HiShell 污染会搞坏 lld）
```

## 包内容
`bin/flang`(+flang-new) · `lib/{libLLVM,libMLIR,libclang-cpp}.so.20.1` · `lib/libFortran{Runtime,Decimal,Common}.a`
· `include/flang/*.mod`（13 个内建模块）。`.so`/`bin/flang` 已 binary-sign-tool 自签。
