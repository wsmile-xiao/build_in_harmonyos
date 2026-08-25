# z3 4.15.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-20
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

z3 使用 CMake 构建系统（不是 autotools）。由于 z3 的 Python 构建脚本不支持 HarmonyOS 平台，必须使用 CMake。

```bash
# 下载源码
curl -k -L https://github.com/Z3Prover/z3/archive/refs/tags/z3-4.15.4.tar.gz -o z3-4.15.4.tar.gz

# 初始化编译环境
python3 $SKILL_ROOT/scripts/ohc-run.py init-build z3 4.15.4 --url=file://$HOME/tmp/downloads/z3-4.15.4.tar.gz

# CMake 配置
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DZ3_BUILD_LIBZ3_SHARED=ON \
  -DZ3_USE_LIB_GMP=OFF \
  -DZ3_BUILD_PYTHON_BINDINGS=OFF \
  -DZ3_BUILD_DOTNET_BINDINGS=OFF \
  -DZ3_BUILD_JAVA_BINDINGS=OFF \
  -DZ3_BUILD_EXECUTABLE=ON \
  -DZ3_BUILD_TEST_EXECUTABLES=OFF \
  -DZ3_INCLUDE_GIT_DESCRIBE=OFF \
  -DZ3_INCLUDE_GIT_HASH=OFF \
  -DCMAKE_CXX_FLAGS="-fPIC -O2" \
  -DCMAKE_EXE_LINKER_FLAGS="-L/storage/Users/currentUser/usr/local/lib" \
  -DCMAKE_SHARED_LINKER_FLAGS="-L/storage/Users/currentUser/usr/local/lib"

# 编译（约 20 分钟）
make -j2

# 安装到 staging 目录
make install DESTDIR=/data/storage/el2/base/cache/test-install-z3-4.15.4

# 安装到本地
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 首次 HTTPS 请求证书问题 | curl -k 下载源码 |
| 2 | Python 构建脚本不支持 HarmonyOS | z3 的 configure 脚本调用 scripts/mk_make.py，不支持 HarmonyOS 平台 | 使用 CMake 构建系统代替 |
| 3 | G0 clean-verify 失败 | ohc-run.py 期望 autotools 构建系统 | 更新 manifest.yaml 指定 cmake 构建系统，创建 hints/cmake-options.txt |

## 源码修改

无补丁。z3 原生支持 CMake 构建系统，在 HarmonyOS 上可直接编译。

## 依赖版本

- cmake 4.1.2
- clang 15.0.4
- Python 3.12.8（构建辅助，不作为运行时依赖）
- 无外部库依赖（Z3_USE_LIB_GMP=OFF）

## 验证结果

```bash
# Staging 验证
$TEST_PREFIX/bin/z3 --version
Z3 version 4.15.4 - 64 bit

$ echo "(declare-const x Int) (assert (> x 100)) (check-sat)" | $TEST_PREFIX/bin/z3 -in
sat

# 本地验证
$ /storage/Users/currentUser/usr/local/bin/z3 --version
Z3 version 4.15.4 - 64 bit
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/z3 | 28M | Z3 可执行文件 |
| lib/libz3.so | 28M | Z3 共享库 |
| include/*.h | 14 个文件 | C/C++ API 头文件 |
| lib/cmake/z3/*.cmake | 4 个文件 | CMake 配置文件 |
| lib/pkgconfig/z3.pc | 1 个文件 | pkg-config 文件 |

## 注意事项

1. z3 使用 CMake 构建系统，不是 autotools。不要尝试运行 ./configure。
2. Z3 的 Python 构建脚本不支持 HarmonyOS，必须使用 CMake。
3. 使用 `-DZ3_USE_LIB_GMP=OFF` 避免 GMP 依赖。
4. 使用 `-DZ3_BUILD_PYTHON_BINDINGS=OFF` 等避免额外绑定依赖。
5. 编译时间较长（约 20 分钟），建议使用 `-j2` 而不是 `-j4` 避免资源耗尽。
6. CMake 会检测到系统为 HarmonyOS（未知系统），但不影响编译。

---

**编译开始**: 2026-05-20 22:42

**编译结束**: 2026-05-20 23:05

**最终状态**: built（编译成功，待打包发布）
<!-- PR submission timestamp: 2026-08-09T04:56:14+08:00 -->
---

**编译结束**: 2026-08-10 01:05
**最终状态**: published
