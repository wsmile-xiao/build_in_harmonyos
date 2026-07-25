# opus 1.5.2 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 libopus.so，供 dlopen 及作依赖。

## 关键适配
- **绕开 conan_toolchain 走裸 cmake**：os=OHOS 下 conan_toolchain 把 CMAKE_SYSTEM_NAME 映射成
  cmake 不认的值（ML-0035：System is unknown to cmake），故 build() 自发现 ohos.toolchain.cmake
  （profile [conf] user_toolchain / OHOS_NDK_HOME / glob SDK 布局）后裸 cmake 交叉编译。
- **装库目录**：ohos.toolchain 64 位默认装 lib64/，用 -DCMAKE_INSTALL_LIBDIR=lib 改回 lib。
- **动态产物**：-DOPUS_BUILD_SHARED_LIBRARY=ON（随 self.options.shared）产 libopus.so 供 dlopen。
- **代码签名**：鸿蒙 PC XPM 要求 dlopen 的 .so 必须签名，否则 Permission denied；package() 用
  binary-sign-tool self-sign（cmake/SDK 自签无效，conan install 复制会破坏链接器自签）。工具路径
  可经 BINARY_SIGN_TOOL/LLVM_OBJCOPY 覆盖，本地无工具时告警跳过（设备加载仍需在 CI/设备签名）。

## 状态
built（CI conan create + test 通过）
