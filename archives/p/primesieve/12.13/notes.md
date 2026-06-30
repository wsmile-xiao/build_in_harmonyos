# primesieve 12.13 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-01
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标平台: OpenHarmony / HarmonyOS (aarch64)
- 状态: published

## 编译步骤

1. **下载源码**: GitHub 直连不通（SSL 证书验证失败 + 连接超时），通过 gh-proxy.com 镜像手动下载 `v12.13.tar.gz`，放置到 `~/tmp/builds/primesieve-12.13.tar.gz` 后运行 init-build（tarball 已存在，跳过下载）
2. **init-build**: `ohc-run.py init-build primesieve 12.13 --url=...`，脚本误判构建系统为 autotools（已手动修正 manifest.yaml 中 `build_system: cmake`）
3. **cmake 配置**: `mkdir build && cd build && cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..`，cmake 识别为 HarmonyOS 未知平台但不影响编译
4. **编译**: `make -j2`，全部 54 个编译单元通过，产出 `libprimesieve.so`、`libprimesieve.a`、`primesieve` 可执行文件
5. **DESTDIR 安装**: `make install DESTDIR=$TEST_PREFIX`，按 R20 铁律正确安装到 staging 目录
6. **启用测试重新配置**: 默认 BUILD_TESTS=OFF，重新 cmake 添加 `-DBUILD_TESTS=ON`，编译 34 个测试程序
7. **运行测试**: `ctest --output-on-failure`，34 个测试全部通过（20.43 秒）
8. **预编译包制作**: `ohc-run.py package primesieve 12.13`（R19 铁律：禁止手动打包）
9. **本地安装验证**: `make install`（不带 DESTDIR），`$DEFAULT_PREFIX/bin/primesieve --version` 输出正确版本号
10. **收尾**: `ohc-run.py finish primesieve 12.13 published`，归档状态 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载失败（SSL 证书验证 + 连接超时） | 本环境无法直连 GitHub，urllib SSL 验证失败 | 使用 gh-proxy.com 镜像手动下载 tarball，放到 ohc-run.py 预期路径后 init-build 自动跳过下载 |
| 2 | init-build 误判构建系统为 autotools | `_guess_build_system()` 基于 URL 模式猜测，GitHub tag URL 不含 cmake 关键字 | 手动修正 manifest.yaml，添加顶层 `build_system: cmake`，修正 `build.system: cmake` |
| 3 | G0 干净构建验证失败 | `clean_verify.py` 仅支持 autotools（`./configure`），对 cmake 项目运行 `./configure` 失败 | 脚本平台限制，手动验证确认 cmake 构建自包含（无补丁、无手动修改源码），不影响发布 |
| 4 | 默认无测试目标（make test 报 No rule） | primesieve CMakeLists.txt 中 `BUILD_TESTS` 默认 OFF | 重新 cmake 配置 `-DBUILD_TESTS=ON`，重建后运行 ctest，34 测试全通过 |
| 5 | DESTDIR staging 中 primesieve --version 失败 | RPATH 指向 `$DEFAULT_PREFIX/lib`，DESTDIR staging 无此路径 | 预期行为（R20 铁律），安装到 `$DEFAULT_PREFIX` 后验证通过 |
| 6 | G4 档案完整性缺少 `build_system:` 字段 | manifest.yaml 模板将 build_system 放在嵌套 `build.system:` 下，而非顶层 | 手动添加顶层 `build_system: cmake` 字段 |
| 7 | 软件级 README.md 缺失 | init-build 骨架创建未生成软件级 README.md | 手动创建 `archives/p/primesieve/README.md`（中文） |

## 源码修改

无补丁。primesieve 12.13 在 OpenHarmony 平台上无需修改源码即可编译通过。

## 依赖版本

无外部依赖。primesieve 是纯 C++ 实现，不依赖任何第三方库。

## 验证结果

```bash
# 版本验证
$DEFAULT_PREFIX/bin/primesieve --version
→ primesieve 12.13, BSD 2-Clause License

# 功能验证（计数质数）
$DEFAULT_PREFIX/bin/primesieve 1000
→ Sieve size = 256 KiB
→ Threads = 1
→ Seconds: 0.000
→ Primes: 168    # 正确：0~1000 之间有 168 个质数

# 测试套件
ctest --output-on-failure
→ 100% tests passed, 0 tests failed out of 34
→ Total Test time (real) = 20.43 sec

# ELF 签名验证
readelf -S $DEFAULT_PREFIX/bin/primesieve | grep codesign
→ [40] .codesign  PROGBITS  (已签名)
readelf -S $DEFAULT_PREFIX/lib/libprimesieve.so | grep codesign
→ [39] .codesign  PROGBITS  (已签名)

# 质量门禁
verify-build primesieve 12.13
→ G1 PASS | G2 PASS(⚠️1) | G3 PASS | G4 PASS
→ 质量报告: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| primesieve-12.13-ohos-aarch64.tar.gz | 1,170 KB | 预编译包（bin/lib/include/cmake/pkgconfig/man） |
| primesieve-12.13-ohos-aarch64-debug.tar.gz | 170 KB | 调试符号包 |

## 注意事项

- cmake 项目需手动启用 `-DBUILD_TESTS=ON` 才可运行测试，默认 OFF
- G0 clean_verify 脚本仅支持 autotools，cmake 项目需手动验证自包含性
- primesieve 链接共享库 `libprimesieve.so`，安装后需确保 `LD_LIBRARY_PATH` 或 RPATH 包含库路径
- CMake 输出 `System is unknown to cmake` 警告，不影响编译和功能
- 无补丁、无源码修改，原始 tarball 即可在 OpenHarmony 上编译通过
- GitHub 直连不通时可使用 gh-proxy.com 镜像下载源码

---
**编译结束**: 2026-06-01 22:00
**最终状态**: published

### 对话 #1 —**摘要**: 2026-06-01 AI 卌 AI 编译协助手)
primesieve v12.13，构建系统为 cmake，无依赖，primesieve 使用 cmake + make ./configure` 选项 `-DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -和 make ` DESTDIR=$TEST_PREFIX`
- 1. 重新 cmake 配置 `-DBUILD_TESTS=ON，，34个测试全部通过
-2. 预编译包制作 `ohc-run.py package primesieve 12.13`（ELF 签名/strip 笡已strip 打本地安装验证 `primesieve --version` 输出正确版本号 12.13