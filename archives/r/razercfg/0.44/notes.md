# razercfg 0.44 适配笔记

## 编译环境
- 构建系统: cmake（project(razer C)，CMake 4.1.2）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（OHOS aarch64 交叉编译）
- 状态: built（conan-verify 全门禁通过）

## 编译步骤

1. conan 注入依赖：`conan install --requires=libusb/1.0.27 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`
2. CMake 配置（OHOS 交叉编译，注入 libusb 私有 prefix）：
   ```bash
   cmake -S $SRC -B $OUT \
     -DCMAKE_TOOLCHAIN_FILE=.../conan_toolchain.cmake \
     -DCMAKE_INCLUDE_PATH=$LIBUSB_PREFIX/include/libusb-1.0 \
     -DCMAKE_LIBRARY_PATH=$LIBUSB_PREFIX/lib \
     -DCMAKE_SHARED_LINKER_FLAGS="-L$LIBUSB_PREFIX/lib" \
     -DCMAKE_EXE_LINKER_FLAGS="-L$LIBUSB_PREFIX/lib" \
     -DRAZERCFG_PKG_BUILD=1
   ```
3. `cmake --build $OUT -j4` → librazer.so + razerd（ui Python 前端已纳入 RAZERCFG_PKG_BUILD 保护不构建）
4. `cmake --install` → bin/（razerd）+ lib/（librazer.so）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | razerd 安装后运行报 `Error loading shared library ../librazer/librazer.so` | CMake 4.1.2 不识别 HarmonyOS 平台，VERSION/SOVERSION 链接命名机制未应用，librazer.so 无 SONAME；razerd 的 NEEDED 记录相对路径 | 补丁 0002：librazer 注入 `LINK_FLAGS "-Wl,-soname,librazer.so"`；补丁 0003：razerd 注入 `LINK_FLAGS "-Wl,-rpath,'$ORIGIN/../lib'"` |
| 2 | cmake install 尝试写 /etc/udev/rules.d、/etc/pm/sleep.d、/usr/lib/systemd/system | 上游 CMake 无条件安装系统级配置文件 | 补丁 0001：用 `RAZERCFG_PKG_BUILD` 环境变量保护系统级 install（与上游 librazer/razerd 已有机制一致） |
| 3 | package_type=application 时 test_package 找不到头文件 | application 类型 CMakeDeps 不导出 cpp_info.libs/includedirs | package_type 改 library + shared/fPIC 选项（razercfg 为库+工具混合型） |
| 4 | 上游 CMake 不安装 librazer 头文件 | 上游 librazer.h 为内部库头（需 RAZERCFG_BUILD 宏） | conanfile package() 手动复制 librazer.h 到 include/librazer/（razer_private.h 为内部私有头，不对外复制） |

## 源码修改

补丁 3 个（见 patches/）：
- 0001-CMakeLists.txt.patch：系统级安装 RAZERCFG_PKG_BUILD 保护
- 0002-librazer-CMakeLists.txt.patch：SONAME 显式注入
- 0003-razerd-CMakeLists.txt.patch：RUNPATH 注入

## 依赖版本

- libusb/1.0.27（制品仓已发布，pkg-config libusb-1.0）

## 验证结果

```bash
conan-verify razercfg 0.44  # G1-G4 + L2/L4/L5 全部 PASS
# 关键产物核验：
readelf -d librazer.so | grep SONAME  # librazer.so ✅
readelf -d razerd | grep -E "NEEDED|RUNPATH"  # NEEDED=librazer.so + RUNPATH=$ORIGIN/../lib ✅
razerd -v  # "Razer device service daemon" ✅
```

上游无测试（R51 清点：无 test 目录/CTest 注册）；test_package 自研 9 条断言（razer_strlcpy 边界/截断、razer_utf16_strlen、razer_ascii_to_utf16，归为 6 组逻辑检查）+ razerd -v 运行验证全部通过。

## 注意事项

- librazer.h 是内部库头（`# error "Do not include this file into your application!"`），下游需定义 RAZERCFG_BUILD 宏才可包含
- 补丁 0002/0003 是 HarmonyOS 平台 CMake SONAME 缺失问题的通用修复范式，详见知识草稿 E000-draft-49C8

**编译结束**: 2026-09-18
**最终状态**: built（conan-verify PASS，W3 本地 CI PASS）
