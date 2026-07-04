# glfw 3.4.6 编译笔记（HarmonyOS PC · Conan cmake，two-pass 定制）

## 定位
- 源码：`ohos_native_glfw` fork（GitCode，分支 3.4.6），XComponent + 桌面 GL 后端。
- 产出**两个互为 `DT_NEEDED` 的 .so**：`libglfw.so.3.4`（soname `libglfw.so.3`）+ `libglfw_bridge.so`。
  两者循环依赖、运行期同 HAP 进程命名空间互相解析符号（ML-0023）。

## 关键适配（相对标准 cmake recipe 的定制）
- **two-pass 双 .so 构建**：`build()` 复刻源码 `build-ohos.sh` 的两遍逻辑——
  - Pass 1：root 工程 + `bridge/` 独立工程各自 `-z undefs` 编出，暂不记 `DT_NEEDED`；
  - Pass 2：root 加 `-DOHOS_BRIDGE_LIBDIR` 重链记 `DT_NEEDED libglfw_bridge.so`，
    bridge 加 `-DOHOS_GLFW_LIBDIR` 重链记 `DT_NEEDED libglfw.so.3`（musl BIND_NOW dlopen 必须）。
- **toolchain 自发现（self-contained）**：`build()` 直接用 OHOS NDK 的 `ohos.toolchain.cmake`（`CMAKE_SYSTEM_NAME=OHOS`
  + 平台模块 → SONAME/版本软链齐），**非** conan 生成的 `conan_toolchain.cmake`（后者 os=OHOS 退化成未知平台
  `HarmonyOS`、不出 SONAME，bridge `-l:libglfw.so.3` 链接失败，ML-0035）。`_ohos_toolchain()` 发现顺序：
  profile `[conf]` user_toolchain → `OHOS_NDK_HOME` → glob `/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake`。
  **不依赖 profile host 段**，故 CI 裸跑即可。
- **cmake 变量**：`GLFW_BUILD_OHOS=ON` + 关 examples/tests/docs + `SHARED` + `-DOHOS_ARCH=arm64-v8a`。
- **系统库**：`ace_napi.z / ace_ndk.z / hilog_ndk.z`（NAPI + XComponent NDK + hilog），写入 `system_libs`。
- **bridge 手动打包**：`bridge/` 无 install target，`package()` 里把 `libglfw_bridge.so` 拷进 `lib/`。
- **签名**：默认关，final link 由链接器自签（ML-0043）；two-pass 的 Pass 2 即 final link，无链接后二进制改动，不需重签。
- `test_package`：`--skip-test-run`，只验编译+链接（GLFW 需 XComponent/HAP 运行期上下文，独立 dlopen 无意义）。

## 状态
- **真机实测通过（HUAWEI MateBook Pro / HAD·2in1，OHOS SDK 26.0.0.18）**：裸跑
  `conan create -pr ohos-native`（无 `-c`、profile host **无** user_toolchain 的 CI 模拟）exit=0，
  test_package 通过；两个 `.so` 均进包，双向 `DT_NEEDED` 齐（`libglfw.so.3.4`→`libglfw_bridge.so`、
  `libglfw_bridge.so`→`libglfw.so.3`），SONAME `libglfw.so.3`。签名走链接器自签（ML-0043，.so 干净未改动）。
- **CI 修复**（v2）：早期版本用 conan_toolchain + `-DUNIX=1`，依赖 profile host 段有 user_toolchain 才出 SONAME，
  CI 因 profile 没配而挂（`System is unknown to cmake` / `-l:libglfw.so.3` 找不到）。改为 `build()` 自发现
  `ohos.toolchain.cmake` 后，recipe 自包含、CI 裸跑通过。
