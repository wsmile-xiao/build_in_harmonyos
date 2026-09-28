# libomptarget-rtl-amdgpu 18.1.8 — 鸿蒙 PC conan 制品

LLVM libomptarget nextgen AMDGPU offloading 运行时插件
（`libomptarget.rtl.amdgpu.so`）的 `os=OHOS, arch=armv8`(= aarch64) conan 包。

## 出包（鸿蒙 PC CI）

```bash
# 鸿蒙 PC 设备原生编译（权威 CI 入口会显式传 profile）
conan create . -pr:h ohos-aarch64 -pr:b ohos-aarch64
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。
> SHA256 实算核对过双通道（本地 Windows 下载 + 设备下载），等于 FreeBSD distinfo 值。

## 构建要点（18.1.8）

- **从 llvm/ 父目录配置**：libomptarget 不允许直接配置（直接配会 FATAL "Direct configuration
  not supported"）。本配方在同一 monorepo 归档内用 `-DLLVM_ENABLE_PROJECTS=openmp` 把 openmp
  挂入 LLVM 构建上下文（`LIBOMPTARGET_LLVM_INCLUDE_DIRS`、`add_llvm_library`、
  `LINK_COMPONENTS Support/Object` 都需要它）。
- **最小 ninja 目标**：`cmake --build --target omptarget.rtl.amdgpu`，ninja 只按依赖闭包编译
  llvm-tblgen + LLVMSupport/LLVMObject 等组件静态库 + 插件本体，不做全量 LLVM
  （llvm/17.0.0 全量实测 2h38m；本包构建约 30 分钟量级）。
- **平台门禁补丁**：上游 amdgpu 插件要求 `CMAKE_SYSTEM_NAME MATCHES "Linux"` 且 processor ∈
  {x86_64,ppc64le,aarch64}，OHOS 宿主（`CMAKE_SYSTEM_NAME=HarmonyOS`）会被静默 `return()`。
  补丁 0002 让 HarmonyOS 与 Linux 同等放行。另设备内核 `uname -p` 返回 unknown，导致
  CMake 探测 `CMAKE_SYSTEM_PROCESSOR=unknown`，配方在 Platform/HarmonyOS.cmake shim 中显式置 aarch64。
- **HSA 依赖为可选 dlopen**：`find_package(hsa-runtime64 QUIET)` 失败时插件走 dynamic_hsa
  （运行期 dlopen libhsa-runtime64.so）。设备无 /dev/kfd、无 ROCm/libhsa，配方用上游 option
  `LIBOMPTARGET_FORCE_DLOPEN_LIBHSA=ON` 钉死该路径。无 GPU 宿主上插件加载后设备数为 0，优雅降级。
- **不构建 amdgcn 位码**：DeviceRTL 位码需要带 AMDGPU 后端的 clang；设备 clang 15.0.4 没有
  amdgcn target。配方用上游开关 `LIBOMPTARGET_BUILD_DEVICERTL_BCLIB=OFF` 关闭，避免强制构建位码。
- **check-* 关闭**：18.1.8 openmp 的 lit 测试目标硬依赖 in-tree clang（`DEPENDS clang`），
  补丁 0001 使 `-DENABLE_CHECK_TARGETS=OFF` 生效，配合 `-DLIBOMP_OMPT_SUPPORT=OFF`
  绕过 check-ompt-multiplex 的直挂 lit 目标。

## .so 签名

OHOS XPM 要求 dlopen 的 .so 代码签名（见 llvm 20.1.0 README / ML-0043）。本配方 `package()`
对 lib/ 下 .so 用 `binary-sign-tool` 显式自签兜底（hnp clang 直链产物一般已自签）。

## 消费

插件不可 `-l` 链接消费：libomptarget 运行时按 `ENABLED_OFFLOAD_PLUGINS` 列表 dlopen 同目录的
`libomptarget.rtl.amdgpu.so`（插件 RPATH=$ORIGIN）。部署时把本包 `lib/` 下 .so 与 libomptarget
置于同一目录即可。

```bash
conan install --requires=libomptarget-rtl-amdgpu/18.1.8 -pr:h ohos-aarch64
# 或展开到 ~/usr/local
conan install --requires=libomptarget-rtl-amdgpu/18.1.8 -pr:h ohos-aarch64 \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

## 上游测试说明

上游 libomptarget 的 lit/check-libomptarget 需要：可执行 amdgcn 镜像的 clang（带 AMDGPU
后端）、in-tree clang/DeviceRTL 位码、AMD GPU + libhsa（/dev/kfd）。鸿蒙 PC 设备三者皆无
（clang 15.0.4 `--print-targets` 无 amdgcn；无 /dev/kfd；无 libhsa），上游测试在本环境不可运行。
本包以 test_package 的 dlopen+dlsym+API 调用作为制品级验证。
