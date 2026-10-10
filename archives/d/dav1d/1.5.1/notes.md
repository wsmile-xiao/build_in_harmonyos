# dav1d 1.5.1 适配笔记（HarmonyOS PC · Conan meson）

## 定位
- dav1d 1.5.0（本仓 archives/d/dav1d/1.5.0）的**升级件**：AV1 解码器，libavif 的解码后端。
- 上游：VideoLAN dav1d，官方 GitHub 镜像 https://github.com/videolan/dav1d（tag `1.5.1`，无 v 前缀）。上游主页 code.videolan.org GitLab 的 archive tarball 与 GitHub 镜像**字节级一致**（实测两源 sha256 同为 fa635e2b…74b695）。
- 1.5.1 为 minor 版本（NEWS: 优化 + 栈缩减：looprestoration 重写降栈到 aarch64 58KB + flush() 死锁修复），API 面（6 个公共头）与 1.5.0 完全一致 → 升级件零 patch 预期。

## 编译环境
- 构建系统: meson（conan MesonToolchain + Meson 包装）
- 编译日期: 2026-10-08
- 编译器: clang/clang++（/data/service/hnp/bin，OHOS SDK 26.0.0.18 自带，clang 即真二进制非 wrapper）
- 主机: HarmonyOS aarch64 真机（与 CI worker 同构——CI profile 无 exe_wrapper，meson test 原生执行）
- 状态: built

## 编译步骤
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
配方内 MesonToolchain 注入：`wrap_mode=nodownload`、`c_std=gnu99`、`enable_tools=false`、`enable_tests=true`、`enable_examples=false`、`enable_docs=false`、`testdata_tests=false`。`build()` 内 `meson.test()` 执行上游注册测试。

## 与 1.5.0 的配方差异（升级件最小增量）
1. `conandata.yml`：URL/sha256 换 1.5.1。**URL 走 GitHub 官方镜像**（github.com/videolan/dav1d archive 格式，与 dav1d/1.5.0 入库形态一致）：实测 code.videolan.org GitLab 对本机与 CI Pre-download 镜像链出口触发 Anubis 反爬挑战（返回 7KB HTML「Making sure you're not a bot!」，sha256 校验必败）；GitHub 官方镜像 tarball 与 GitLab 字节级一致（sha256 同），且 CI 对 GitHub URL 自动加镜像 fallback。
2. `enable_tests=true` + `meson.test()`：1.5.0 是 `enable_tests=false`（当时未统计上游套件）；1.5.1 对齐同源 libdav1d/1.5.4 先例启用上游测试注册并真机执行（构建机即 OHOS 真机）。`cross_building` 守卫：真交叉环境只验编译不执行。
3. `package_info()` 补 `system_libs=["pthread","m"]`（meson.build 链接面：thread/dl/m 依赖，dl 由 musl 并入 libc）。
4. 启用 asm（默认）：1.5.0 已实证 aarch64 asm 路径在 OHOS clang 下编译通过（is_asm_enabled 对 aarch64 恒真，clang 集成汇编器直接编 .S；gas-preprocessor 仅 MSVC arm 需要）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson has_function 对 clock_gettime 检测失败 → `error('clock_gettime not found')` | musl 严格 C99 不声明 POSIX 函数（glibc 默认开 _DEFAULT_SOURCE 无此问题） | `c_std=gnu99`（1.5.0 实证，1.5.1 沿用） |
| 2 | meson configure 报找不到 llvm-ar | conan MesonToolchain 不把 ar/ranlib 写进 native file | `_inject_meson_archiver()` 从编译器同目录推导全路径注入（cairo 1.18.4 实证） |
| 3 | dlopen libdav1d.so 报 Permission denied | 鸿蒙 XPM 代码签名要求；conan install 复制破坏链接器自签 | `package()` 内 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 重签 |
| 4 | （升级件）1.5.0→1.5.1 源码差异是否破坏配方 | 1.5.1 仅优化/修 bug，meson_options 键名与 6 头文件 API 面不变 | 零 patch，配方直接沿用 1.5.0 骨架 |

## 上游测试口径（真实统计）
- `tests/meson.build` 注册：`test(target, ...)` foreach `dav1d_api_headers` = **6 个头文件 API 测试**（common/data/dav1d/headers/picture/version `.h_test`，各自独立编译 `header_test.c` 验证头自包含）。
- `checkasm`（`test('checkasm', ...)`）仅在 `is_asm_enabled` 时注册——本配方 asm 开启时注册，aarch64 用 clang 集成汇编器编译 checkasm_64.S，无需外部 checkasm wrap 依赖（subprojects/ 目录在 release tarball 中不存在，1.5.4 notes 的"需外部 checkasm 依赖"结论基于 C-only 视角）。
- `dav1d-test-data` 语料测试：`testdata_tests=false`（需独立测试数据仓，release tarball 不含）。
- `seek_stress`：`enable_seek_stress`（默认 false）且依赖 CLI 工具（本包 enable_tools=false），不注册。
- libfuzzer 二进制（dav1d_fuzzer 等）：构建产物，非注册测试。

## 验证结果
见 `test_package/MANIFEST.yml` 与 PR 正文统计表：上游 6 头文件测试 + checkasm 由 `meson.test()` 真机执行；test_package 消费者测试链接交付的 libdav1d.so 走完整生命周期断言。

## 依赖版本
- 无 conan 依赖（requirements 空）；系统库 pthread/m/dl。

## 注意事项
- 产可执行文件的下游（如开启 tools）需签 bin/——本包 enable_tools=false 无 bin 产物。
- 1.5.1 对栈需求更低（aarch64 58KB），线程栈敏感的宿主（libavif 插件加载场景）受益。
