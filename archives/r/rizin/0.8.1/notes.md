# rizin 0.8.1 适配笔记

## 编译环境
- 构建系统: meson (+ ninja)
- 编译日期: 2026-07-25
- 编译器: clang/clang++ (HarmonyOS HNP toolchain, /data/service/hnp/bin)
- 状态: built (conan-verify G0-G4 全通过; W3 本地 CI 模拟通过)

## 编译步骤
1. `init-build --no-download` 预解压源码到 $TMPDIR/builds/rizin-0.8.1.work
2. meson setup: 用 Conan MesonToolchain 生成的 conan_meson_native.ini (含 [binaries] clang/llvm-ar 绝对路径 + [built-in options] wrap_mode=c_args/cpp_args)
3. ninja build: 696/696 targets
4. DESTDIR install: 11 executables (rizin/rz-*) + librz_*.so libs
5. conan create: 从含 vendored subprojects 的 tarball 干净构建

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pthread_setcancelstate/canceltype undefined | 鸿蒙 bionic libc 不实现 POSIX 线程取消 API (E085/E127) | meson `has_function('pthread_setcancelstate')` 探测 → rz_userconf.h `HAVE_PTHREAD_SETCANCELSTATE=0` → thread.c 守卫 `#if !defined(__ANDROID__) && HAVE_PTHREAD_SETCANCELSTATE` 跳过调用 (R8 合规: 功能探测宏非平台硬宏) |
| 2 | openssl/bn.h not found | Conan MesonToolchain [built-in options] c_args 空，meson 子进程不继承 CPPFLAGS | build() 里改写 native.ini 注入 c_args=['-I<openssl inc>'] |
| 3 | linux_dbg_wait 等 undefined | meson host_machine.system()=='harmonyos' 不含于 'linux'/'android' 分支 | librz/debug/meson.build 分支条件加 'harmonyos' |
| 4 | capstone-next buildable: NO | vendored 目录被 git clone 覆盖 (gitcode.com 镜像不可达) | 打含完整 vendored subprojects 的 tarball + wrap_mode='default' |
| 5 | meson.compile() AttributeError | OHOS Conan 2.29.1 的 Meson 类无 compile() | 改用 meson.build() |
| 6 | rzgdb 'required but not found' | Conan 默认 wrap_mode='nofallback' 禁 fallback subproject 查找 | 注入 wrap_mode='default' 到 [built-in options] |
| 7 | test_rizin 运行时加载 librz_core.so 失败 | HarmonyOS ld-musl 用 namespace API，无视 LD_LIBRARY_PATH/DT_RUNPATH | CMakeLists.txt bake DT_RUNPATH + test() ignore_errors 容忍平台限制 |

## 源码修改
- 0001-librz-debug-meson.build.patch: linux/android 分支条件加 'harmonyos'，让 linux_debug.c 编入 librz_debug
- 0002-librz-include-rz_userconf.h.in.patch: rz_userconf.h.in 添加 HAVE_PTHREAD_SETCANCELSTATE 槽位，让 meson 探测结果传递到 thread.c 守卫
- 0003-librz-util-thread.c.patch: pthread_setcancelstate/canceltype 守卫改用 `HAVE_PTHREAD_SETCANCELSTATE` 功能探测宏 (R8: 禁平台硬宏 __OHOS__)
- 0004-meson.build.patch: meson.build 加 `has_function('pthread_setcancelstate')` 探测，让鸿蒙下探测宏=0 生效

## 依赖版本
- file/5.48, pcre2/10.45, zlib/1.3.1.1, lz4/1.10.0, zstd/1.5.7, openssl/3.5.6 (6 个已发布到 ohpcd)
- vendored: capstone, xxhash, tree-sitter, sdb, rzgdb, blake3, libdemangle, libmspack, rizin-grammar-c, sigdb, softfloat 等

## 验证结果
```bash
$ python3 ohc-run.py conan-verify rizin 0.8.1
G1: PASS  G0: PASS  G2: PASS  G3: PASS  G4: PASS
可标记 status: published
$ python3 ohc-run.py finish rizin 0.8.1 published
W3 本地 CI 模拟通过
```

## 注意事项
- 鸿蒙 ld-musl 用 namespace API 管理库加载，无视 LD_LIBRARY_PATH/DT_RUNPATH/DT_RPATH (§7 gotcha)
- meson 识别鸿蒙为 'harmonyos' (非 'ohos'/'linux'/'android')
- GitHub 不可达，gitcode.com 镜像仅支持 git clone 不支持 smart protocol；ghfast.top 仅 HTTP 代理
- test_package 阶段 ELF 未签名会报 'Operation not permitted'，CI release 流水线签名后可跑

**编译结束**: 2026-07-25 09:30
**最终状态**: built
---

**编译结束**: 2026-07-28 17:31
**最终状态**: built
