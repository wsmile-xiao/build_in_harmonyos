# kdegraphics-mobipocket 26.04.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 目标平台: OpenHarmony NEXT (aarch64, musl libc, clang 15.0.4)
- 状态: built

## 编译步骤

1. cmake配置:
```bash
cd /storage/Users/currentUser/tmp/builds/kdegraphics-mobipocket-26.04.1.work/build
cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_TESTING=OFF \
      -DKF_IGNORE_PLATFORM_CHECK=TRUE \
      -DCMAKE_C_COMPILER=clang \
      -DCMAKE_CXX_COMPILER=clang++
```
2. make 编译成功
3. make install DESTDIR=/storage/Users/currentUser/tmp/test-install-kdegraphics-mobipocket-26.04.1 (staging install)

## 遶到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 平台检查失败 | OHOS 不在 KDE 支持平台列表中 | KF_IGNORE_PLATFORM_CHECK=TRUE |
| 2 | mobidump 未安装 | tools/CMakeLists.txt 无 install 命令（仅用于测试） | 非问题，库和头文件正常安装 |

## 源码修改

无源码修改，所有适配通过 cmake 选项完成。

## 依赖版本

- Qt6: 6.11.1
- ECM: 6.20.0

## 验证结果

- libQMobipocket6.so 库已编译
- 3 个头文件已安装
- 4 个 cmake config 文件已安装
- mobidump 测试工具已编译但未安装（仅用于测试）

## 交付物

| 文件 | 说明 |
|------|------|
| kdegraphics-mobipocket-26.04.1-ohos-aarch64.tar.gz | 主包 (lib + headers + cmake configs) |
| kdegraphics-mobipocket-26.04.1-ohos-aarch64-debug.tar.gz | 调试符号包 |

## 注意事项

- mobidump 是测试工具，上游未定义 install target
- 库依赖于 Qt6Core 和 Qt6Gui
---

**编译结束**: 2026-08-07 02:03
**最终状态**: built
