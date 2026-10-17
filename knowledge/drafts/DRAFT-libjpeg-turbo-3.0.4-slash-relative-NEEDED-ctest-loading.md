# DRAFT-libjpeg-turbo-3.0.4-slash-relative-NEEDED-ctest-loading — 斜杠相对 NEEDED 的加载语义与 ctest 修复

> **Contributor**: pc2-3 | **Status**: DRAFT | **Updated**: 2026-09-05
> **Severity**: medium | **Category**: platform / loading / cmake / test
> **Audience**: 任何在 build 目录内跑 ctest 的 CMake C 库执行端（libjpeg-turbo 3.0.4 及同类）

## 问题签名

```text
Error loading shared library ../libjpeg.so: (needed by ./djpeg)
Error relocating ./djpeg: jpeg_std_error: symbol not found
51% tests passed, 281 tests failed out of 574   （首轮）
65% tests passed, 201 tests failed out of 574   （加 LD_LIBRARY_PATH 后，12-bit 组仍全挂）
```

## 根因

`readelf -d build-native/djpeg` 显示 `NEEDED [../libjpeg.so]` —— 链接器把共享库写成
**含斜杠的相对路径**。glibc 动态加载器对含 `/` 的 NEEDED 条目**按进程 cwd 解析**，
不走 LD_LIBRARY_PATH / RPATH / RUNPATH：

- ctest 各用例进程 cwd = `build-native/` → 加载器找 `build-native/../libjpeg.so`
  （即 .work 根目录）；
- 无文件 → `Error loading shared library ../libjpeg.so`；
- 有旧库 → 符号不匹配 → `Error relocating ... symbol not found`。

本机实测：首轮 281 失败（共享库整体加载失败），二轮加 LD_LIBRARY_PATH 后 201 失败
（12-bit 用例全部命中该 NEEDED 语义）。两者都证明 LD_LIBRARY_PATH 无效。

## 修复（parent-dir-symlink）

在 cwd 的父目录放置指向真实 .so 的符号链接，使 `../libjpeg.so` 按 cwd 解析成功：

```bash
ln -sf build-native/libjpeg.so ../libjpeg.so
ln -sf build-native/libturbojpeg.so ../libturbojpeg.so
cd build-native && LD_LIBRARY_PATH=$PWD ctest --output-on-failure -j4
# → 100% tests passed, 0 tests failed out of 574
```

（LD_LIBRARY_PATH 仍保留，覆盖无斜杠 NEEDED 的库如 libturbojpeg.so 的依赖。）

## 验证

- run1: 51% passed, 281 failed（无修复）
- run2: 65% passed, 201 failed（仅 LD_LIBRARY_PATH，斜杠 NEEDED 不受控）
- run3: 100% passed, 0 failed out of 574（父目录符号链接 + LD_LIBRARY_PATH）
- 证据日志: upstream_test_build.log / upstream_test_run2.log / upstream_test_run3.log
  （run3 sha256 8fb5717e84c2eec5fc7f9c9c843dd4b4a3970f48b5f68252bb145bb0b5717529）

## 适用边界 / 反例

- 适用：CMake 构建树内工具以 `-L.. -l<lib>` 或等价形式链接共享库的库；
  OHOS/CI 编译后直接在 build 目录跑 ctest 的执行端。
- 反例：纯静态链接库、或工具以绝对路径/`$ORIGIN` RUNPATH 链接的库不受影响；
  生产安装后（SONAME basename）无此问题——仅**未安装的构建树内运行**出现。
- 与 E019（LD_LIBRARY_PATH）/E042（RPATH patchelf）区别：斜杠相对 NEEDED 不经过
  LD_LIBRARY_PATH/RPATH，必须按加载器 cwd 语义处理，不能用常规手段绕过。

## 关系

- similar_to: E019, E078, E088, E131, E135, E502（共享库加载/符号解析类，但方案不同）
- 无既有条目覆盖"斜杠相对 NEEDED 按 cwd 解析"这一具体机制
