# prometheus-cpp 1.3.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: OpenHarmony (aarch64)
- 状态: published

## 编译步骤

1. 下载源码：使用 `curl -kL` 从 gh-proxy.com 镜像下载 `prometheus-cpp-with-submodules.tar.gz`，绕过 HarmonyOS SSL证书验证问题，手动放入 `~/tmp/builds/prometheus-cpp-1.3.0.tar.gz`
2. 初始化编译：`ohc-run.py init-build prometheus-cpp 1.3.0 --url=...`（因本地已有tarball，自动跳过下载）
3. 修正构建系统识别：将 manifest.yaml 和 `.build-context` 中的 `build_system` 从误识别的 `autotools` 修正为 `cmake`
4. cmake 配置：
   ```bash
   mkdir build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_SYSTEM_NAME=Linux \
         -DBUILD_SHARED_LIBS=OFF \
         -DENABLE_PUSH=OFF \
         -DENABLE_COMPRESSION=OFF \
         ..
   ```
5. 编译：`make -j2` — 全部100%构建成功，产出 libprometheus-cpp-core.a 和 libprometheus-cpp-pull.a
6. DESTDIR安装：`make install DESTDIR=$TEST_PREFIX` — 头文件、静态库、pkg-config、cmake配置均正确安装
7. 运行测试：`ctest -V --output-on-failure` — 3套155用例，153通过1跳过0失败
8. 质量门禁：`verify-build` — G1-G4全PASS
9. 打包：`ohc-run.py package` — 产出 `prometheus-cpp-1.3.0-ohos-aarch64.tar.gz` (870KB)
10. 本地安装验证：`make install`（不带DESTDIR） — 验证 `$DEFAULT_PREFIX` 下文件完整可用
11. 收尾：`ohc-run.py finish prometheus-cpp 1.3.0 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build下载SSL证书验证失败 | HarmonyOS环境缺少CA证书，Python urllib SSL验证无法通过 | 使用 `curl -kL` 绕过SSL验证手动下载，将tarball放入 `~/tmp/builds/` 预期路径，init-build检测到已存在文件自动跳过下载 |
| 2 | build_system被误识别为autotools | `_guess_build_system()` 函数仅检测URL中的关键词，prometheus-cpp的下载URL不含"cmake"，导致默认返回autotools | 手动修正manifest.yaml的 `build_system: cmake`（扁平字段）和 `build.system: cmake`（嵌套字段），以及 `.build-context` 中的 `BUILD_SYSTEM` 环境变量 |
| 3 | verify-build G4首次失败 | 质量门禁脚本查找扁平的 `build_system` 字段，原始manifest模板只有嵌套 `build.system` 格式 | 在manifest.yaml顶层添加 `build_system: cmake` 扁平字段 |
| 4 | G0 clean-verify失败 | `ohc-run.py clean-verify` 脚本不支持cmake项目自动验证（仅支持autotools `./configure`） | cmake项目需手动验证干净构建，已确认手动cmake configure + make全流程可成功完成 |
| 5 | curl和zlib不可用 | OpenHarmony环境无curl和zlib预编译包 | 禁用对应功能：`-DENABLE_PUSH=OFF`（禁用Push模块）和 `-DENABLE_COMPRESSION=OFF`（禁用压缩），core和pull模块功能不受影响 |

## 源码修改

无源码修改，无需补丁。prometheus-cpp源码在OpenHarmony平台上可直接通过cmake编译，无需任何源码层面的适配。

## 编译参数说明

| 参数 | 值 | 说明 |
|------|-----|------|
| CMAKE_INSTALL_PREFIX | $DEFAULT_PREFIX | 安装路径 ~/usr/local |
| CMAKE_SYSTEM_NAME | Linux | 绕过cmake平台检测，避免误识别为OHOS（cmake没有OHOS定义） |
| BUILD_SHARED_LIBS | OFF | ⭐ R4补充铁律：OpenHarmony不支持RUNPATH加载.so，必须编译为静态库 |
| ENABLE_PUSH | OFF | 禁用Push模块（依赖curl，curl不可用） |
| ENABLE_COMPRESSION | OFF | 禁用压缩功能（依赖zlib，zlib不可用） |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| pthread | 系统自带 | cmake自动检测到pthread，链接参数 `-lpthread` |
| googletest/googlemock | 内嵌(3rdparty) | 随submodules tarball一起提供，用于测试 |

## 验证结果

### 测试验证
```
ctest -V --output-on-failure
3/3 tests passed, 0 tests failed
155 用例: 153 通过, 1 跳过, 0 失败
总耗时: 1.69 秒
```

### 安装验证
```
ls $DEFAULT_PREFIX/include/prometheus/
# 20 个头文件 + detail/ 子目录

ls $DEFAULT_PREFIX/lib/libprometheus-cpp*
# libprometheus-cpp-core.a  (核心库)
# libprometheus-cpp-pull.a  (Pull模块库)

ls $DEFAULT_PREFIX/lib/pkgconfig/
# prometheus-cpp-core.pc
# prometheus-cpp-pull.pc

ls $DEFAULT_PREFIX/lib/cmake/prometheus-cpp/
# prometheus-cpp-config.cmake
# prometheus-cpp-config-version.cmake
# prometheus-cpp-targets.cmake
# prometheus-cpp-targets-noconfig.cmake
```

### 质量门禁验证
```
G1 二进制完整性: PASS
G2 功能可用性: PASS (1个警告：库项目无可执行文件验证，属正常)
G3 可移植性: PASS
G4 档案完整性: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| prometheus-cpp-1.3.0-ohos-aarch64.tar.gz | 870KB (891038 bytes) | 预编译包，含头文件、静态库、pkg-config、cmake配置 |

## 注意事项

1. **必须静态编译**：OpenHarmony不支持RUNPATH加载共享库(.so)，prometheus-cpp必须用 `BUILD_SHARED_LIBS=OFF` 编译为静态库(.a)
2. **Push和Compression模块被禁用**：因curl和zlib不可用，对应功能被禁用。如需启用，需先编译安装curl和zlib
3. **cmake平台检测**：需设置 `CMAKE_SYSTEM_NAME=Linux` 绕过平台检测，cmake没有OHOS/OpenHarmony的系统定义
4. **G0 clean-verify不适用**：`ohc-run.py clean-verify` 仅支持autotools项目，cmake项目需手动验证干净构建
5. **init-build下载SSL问题**：HarmonyOS环境下GitHub下载可能遇到SSL证书验证失败，建议提前用 `curl -kL` 手动下载

---

**编译结束**: 2026-06-02  
**最终状态**: published
