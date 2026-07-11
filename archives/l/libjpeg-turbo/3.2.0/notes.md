# libjpeg-turbo 3.2.0 编译笔记（HarmonyOS PC · Conan cmake）

## 定位
- JPEG 编解码库，本次作为 **libtiff 的 Conan 依赖** 先行适配。
- 产出 `libjpeg.so`（经典 libjpeg API，SONAME `libjpeg.so.62`，下游 libtiff 走 `-ljpeg`）
  + `libturbojpeg.so`（TurboJPEG API）。`package_info.libs = ['jpeg', 'turbojpeg']`。

## 构建方式（与 glfw/3.4.6 同法：自发现 toolchain + 裸 cmake）
`build()` 里 `_ohos_toolchain()` **自发现** OHOS NDK 的 `ohos.toolchain.cmake`（① profile [conf] 的
user_toolchain ② 环境 `OHOS_NDK_HOME` ③ glob `/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/`），
再用裸 `cmake -B ... -DCMAKE_TOOLCHAIN_FILE=<它>` 构建——**不经 conan_toolchain**，故 recipe 自包含、
**不依赖 CI profile 的 host 段**（裸 `conan create` 即可，无需 `-c:h`）。关键 `-D`：
- `-DCMAKE_INSTALL_LIBDIR=lib`：ohos.toolchain 在 64 位默认装 `lib64/`，须强制 `lib/` 与 conan cpp_info 一致。
- `-DENABLE_STATIC=OFF`：只出共享库；`-DWITH_TOOLS=OFF`/`-DWITH_TESTS=OFF`：精简。
- `-DWITH_SIMD=OFF`：E096，OHOS 上 SIMD 链接失败须禁（沿用 2.1.5.1/3.1.4.1 结论），代价 JPEG 慢 2–6×。
`package()` 装完调 `_sign_shared_libs()` 重签 `.so`。

## 真机验证踩坑（4 个根因，逐个暴露，均已固化进 conanfile）
真机裸 `conan create -pr ohos-native` 迭代到通，依次踩：
1. **ML-0035 —— cmake 不认识 OHOS 系统**（用 conan_toolchain 时 `System is unknown to cmake`）。
   → 改自发现 `ohos.toolchain.cmake` + 裸 cmake，绕开 conan_toolchain。
2. **GNUInstallDirs `set_property(CACHE CMAKE_INSTALL_*)` 报错**（conan_toolchain 预设这些为普通变量所致）。
   → 绕开 conan_toolchain 后自然消失。
3. **dlopen `Permission denied`（代码签名）**：SDK toolchain 产的 `.so` 自签无效。
   → `package()` 用 `objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 重签。
4. **dlopen `No such file or directory`**：ohos.toolchain 64 位把库装进 `lib64/`，而 conan/test 找 `lib/`。
   → `-DCMAKE_INSTALL_LIBDIR=lib`。

## 复核点（非阻塞）
- **R26（系统同名库）**：`libjpeg` 是系统库名，本配方按 libpng/glfw 先例出**共享库**；若真机存在系统
  `libjpeg.so*` 运行期冲突再改静态 + `-fPIC`。当前验证环境未见冲突。
- **R40（多媒体库）**：test_package 为 R34 反空壳（dlopen + dlsym `jpeg_std_error`，真机已过）；未做真实 encode/decode。
- **WITH_SIMD=OFF 代价**：JPEG 慢 2–6×，后续可另开验证试重启 NEON。

## 离线源码（CI/设备无 github 直连时）
设备拉 `release-assets.githubusercontent.com` 超时时：mac 下好 tarball → `hdc file send` → 放进 conan
download 缓存（`core.download:download_cache=<dir>` + 文件按 sha256 命名）即可离线 `source()`。CI 环境同理。

## 状态
**built（真机已验，CI-portable）** — 2026-07-11 在 HarmonyOS PC(2in1, 3QC0124C11000718, ohos-sdk 26.0.0.18)
**裸** `conan create -pr ohos-native`（**不带 -c:h**）通过：test_package `dlopen libjpeg.so ok`（dlsym
`jpeg_std_error`），产物 `lib/libjpeg.so.62.4.0` **SONAME=libjpeg.so.62** + `libturbojpeg.so.0.5.0`，`.so` 已 selfSign。
