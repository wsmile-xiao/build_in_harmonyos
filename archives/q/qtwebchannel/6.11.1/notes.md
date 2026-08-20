# qtwebchannel 6.11.1 适配笔记

## 编译环境
- 构建系统: cmake (Qt 6 module, qmake .pro 由 CMake 驱动)
- 编译日期: 2026-08-19
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built (conan 验证后更新为 published)

## 编译步骤

1. init-build: 下载官方 Qt 子模块源码
   `https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qtwebchannel-everywhere-src-6.11.1.tar.xz`
   (SHA256: 69fbb50b71d6e6596c2d6863ee9a9c984a4d01378ee2b7b4163bb467a0158d82)
2. 手动探索编译（依赖制品仓发布的 qtbase/6.11.1 预编译包）:
   ```
   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
     -DQt6_DIR=$QTBA/lib/cmake/Qt6 \
     -DQT_QMAKE_TARGET_MKSPEC=harmonyos-clang \
     -DQT_BUILD_TESTS=ON -DQT_BUILD_TESTS_BY_DEFAULT=ON \
     -DQT_BUILD_EXAMPLES=OFF -DQT_BUILD_BENCHMARKS=OFF -DQT_BUILD_MANUAL_TESTS=OFF
   cmake --build build -j1
   ```
3. 上游测试: `ctest --test-dir build --output-on-failure -j1`（需 LD_LIBRARY_PATH 指向 qtbase lib）
4. conan-init 生成配方（autotools 模板有误，已按 qtwebsockets/6.11.1 参考重写为 CMake 配方）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ctest 运行时 `symbol not found`（Qt6Core 符号） | LD_LIBRARY_PATH 未包含 qtbase 包的 lib 目录 | 运行时 export LD_LIBRARY_PATH=$QTBA/lib（VirtualRunEnv 处理） |
| 2 | module_includes 上游测试失败 | 单模块构建树导出时 Qt6::Core 仅以 IMPORTED_LINK_DEPENDENT_LIBRARIES 声明（不传播 INTERFACE_INCLUDE_DIRECTORIES），该测试面向完整 Qt 源码树构建 | 平台/构建模式限制，非本模块缺陷；功能测试 tst_webchannel 通过，等价消费者覆盖由 test_package 提供 |
| 3 | conan-init 生成 autotools 模板 | 模板检测把 Qt 模块识别为 autotools | 按同版本已发布模块 qtwebsockets/6.11.1 的 CMake 配方模式重写 |

## 依赖版本
- qtbase/6.11.1（制品仓 ohpcd 已发布）
- qtdeclarative/6.11.1（制品仓 ohpcd 已发布，提供 Quick/QuickTest 可选组件）
- qtshadertools/6.11.1（qtdeclarative 传递依赖，已发布）

## 验证结果

```bash
# 库构建 + 链接
libQt6WebChannel.so 构建成功
# 上游功能测试
ctest -R '^tst_webchannel$' --output-on-failure  # PASSED (11.5s)
# module_includes 为完整源码树构建模式的集成测试，单模块构建下受限（见上表 #2）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方，复用 Qt 原生 CMake 包文件（cmake_find_mode=none） |
| conandata.yml | 官方源码 URL + SHA256 |
| test_package/ | 消费者测试（QWebChannel 注册/查询/注销 + transport 验证） |
| patches/ | 无（无需源码补丁） |

## 注意事项
- 本模块为 Qt WebEngine 的必要依赖（qtwebengine 的 WebChannel API 硬依赖它）
- 上游测试：tst_webchannel 通过；module_includes 为构建模式限制（非阻塞）
- settings.os 判断使用 `in ("Linux", "OHOS")`（R32）
---

**编译结束**: 2026-08-19 23:59
**最终状态**: published
