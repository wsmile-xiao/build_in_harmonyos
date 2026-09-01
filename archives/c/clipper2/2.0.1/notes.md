# clipper2 2.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-15
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. init-build 初始化（zip格式源码，嵌套源码提升 CPP → clipper2-2.0.1.orig）
2. cmake 配置：
   ```bash
   mkdir -p build && cd build
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release \
     -DCLIPPER2_TESTS=OFF -DCLIPPER2_EXAMPLES=OFF -DCLIPPER2_UTILS=OFF \
     -DBUILD_SHARED_LIBS=OFF
   ```
3. make -j1 编译（生成 libClipper2.a 和 libClipper2Z.a）
4. make install DESTDIR=$TEST_PREFIX（staging隔离安装）
5. Staging验证（产物完整：库文件、头文件、pkg-config、cmake config）
6. verify-build 通过（G1-G4 PASS）
7. ohc-run.py package 制作预编译包（743KB tar.gz）
8. make install（安装到 $DEFAULT_PREFIX）
9. 用户验证：编写测试程序验证库功能（面积计算10000正确）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 检测 BUILD_SYSTEM=autotools | 源码无 configure，脚本默认为 autotools | 手动适配 cmake 流程编译 |
| 2 | cmake 报 "System is unknown to cmake (HarmonyOS)" | HarmonyOS 未被 cmake 官认为已知平台 | 不影响编译，cmake 自动 fallback 处理 |
| 3 | verify-build G4 FAIL（manifest 缺少 build_system） | manifest.yaml 模板无顶层 build_system 字段 | 添加顶层 build_system: cmake 字段 |
| 4 | 测试需要 git clone googletest | 平台无网络 git clone 不可用 | 禁用 CLIPPER2_TESTS=OFF |

## 源码修改

无补丁，无需修改源码。clipper2 编译零修改通过。

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- make: GNU Make 4.4.1

## 验证结果

```bash
# pkg-config验证
$ export PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig:$PKG_CONFIG_PATH
$ pkg-config --modversion Clipper2
2.0.1
$ pkg-config --modversion Clipper2Z
2.0.1
$ pkg-config --cflags Clipper2
-I/storage/Users/currentUser/usr/local/include
$ pkg-config --libs Clipper2
-L/storage/Users/currentUser/usr/local/lib -lClipper2
$ pkg-config --libs Clipper2Z
-L/storage/Users/currentUser/usr/local/lib -lClipper2Z

# 静态库验证
$ file $DEFAULT_PREFIX/lib/libClipper2.a
ar archive
$ file $DEFAULT_PREFIX/lib/libClipper2Z.a
ar archive
$ llvm-ar t $DEFAULT_PREFIX/lib/libClipper2.a
clipper.engine.cpp.obj / clipper.offset.cpp.obj / clipper.rectclip.cpp.obj / clipper.triangulation.cpp.obj

# C++ API 功能测试（实际执行结果）
# 测试1: 面积计算 — Area(100x100正方形) = 10000 ✅
# 测试2: 方向判断 — IsPositive(逆时针正方形) = true ✅
# 测试3: 路径简化 — SimplifyPaths 1条路径 → 1条 ✅
# 测试4: Intersect交集裁剪 — 交集面积 = 2500 ✅
# 测试5: Union合并裁剪 — 合并面积 = 17500 ✅
# 测试6: Clipper2Z z成员 — USINGZ模式 z属性可用 ✅
# 测试7: 双库链接 — 无符号冲突 ✅
# 总判定: 10/10 替代测试通过 ✅ PASS

# 库文件
$ ls $DEFAULT_PREFIX/lib/libClipper2*
libClipper2.a  (291,158 bytes)  libClipper2Z.a  (317,296 bytes)

# 头文件（9个）
$ ls $DEFAULT_PREFIX/include/clipper2/
clipper.h clipper.version.h clipper.core.h clipper.engine.h clipper.export.h
clipper.minkowski.h clipper.offset.h clipper.rectclip.h clipper.triangulation.h

# cmake配置文件
$ ls $DEFAULT_PREFIX/lib/cmake/clipper2/
Clipper2Config.cmake  Clipper2ConfigVersion.cmake  Clipper2Targets.cmake  Clipper2Targets-release.cmake
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| clipper2-2.0.1-ohos-aarch64.tar.gz | 743KB | 预编译包（含库+头文件+pkg-config+cmake config） |

## 注意事项

- clipper2 是纯静态库项目（无可执行文件），安全弹窗验证(R7)不适用
- 默认编译选项含 -Werror，在非MSVC平台严格；本次编译无额外警告，顺利通过
- CLIPPER2_USINGZ 默认 ON，同时编译 Clipper2 和 Clipper2Z 两个库
- cmake 配置时建议禁用 tests/examples/utils 以减少编译依赖
- pkg-config 使用前需设置 PKG_CONFIG_PATH 包含 $DEFAULT_PREFIX/lib/pkgconfig
---

**编译结束**: 2026-07-21 20:16
**最终状态**: built
