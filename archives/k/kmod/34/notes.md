# kmod 34 适配笔记

## 编译环境
- 构建系统: meson（kmod 34 上游主构建；autotools 保留仅为兼容）
- 编译日期: 2026-09-05
- 编译器: clang 15 / clang++（/data/service/hnp/bin，OHOS SDK）
- profile: ci/conan/profiles/ohos-aarch64（os=OHOS 6.0, armv8, libc++, cppstd=17）
- 状态: built（conan create 端到端通过，未上传 ohpcd）

## 编译步骤
```
cd archives/k/kmod/34
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
- meson options: `-Dmanpages=false`（无 scdoc）`-Dbuild-tests=false`（testsuite 无法在 OHOS 运行，见下）
  `-Dzstd=enabled -Dxz=enabled -Dzlib=enabled -Dopenssl=enabled`（压缩 + PKCS7 签名全开）
- 产物：libkmod.so.2.5.1 + kmod/depmod/modinfo/insmod/rmmod/lsmod/modprobe（sbin 下为相对符号链接）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 报 `settings.os.version value not defined` | 本机 default profile 无 os.version，而 zstd 配方声明了它 | 用 CI 的 ohos-aarch64 profile（os.version=6.0 + libc++ + cppstd=17） |
| 2 | meson configure: `Unknown linker(s): llvm-ar, ar` | MesonToolchain 未注入 ar/ranlib | 移植 glib 配方的 `_inject_meson_binaries()`（注入 ar/ranlib/pkg-config 到 conan_meson_native.ini） |
| 3 | meson configure: `Dependency liblzma not found` | 发布配方经 PkgConfigDeps 生成 xz.pc/openssl.pc，meson 要 liblzma/libcrypto | `_alias_pc_files()`：xz.pc→liblzma.pc、openssl.pc→libcrypto.pc（glib pcre2 同款） |
| 4 | 编译报 `program_invocation_short_name` undeclared | OHOS musl 无 glibc 扩展符号 | 补丁：kmod.h 声明 + log.c 以 `__progname` 初始化并计算 basename（E493/E203 同族，补丁不用 __OHOS__） |
| 5 | 编译报 `get_current_dir_name` 隐式声明 | glibc 扩展函数，musl 无 | 补丁：shared/util.c `#define get_current_dir_name() getcwd(NULL, 0)`（POSIX 等价） |
| 6 | package() 报 `ln: Unknown option 'symbolic'` | OHOS toybox ln 不支持 `--symbolic/--relative` 长选项 | 补丁：meson.build 安装脚本加 `|| true` 容错；配方 package() 用 python os.symlink 创建 sbin/<tool>→../bin/kmod |
| 7 | test_package 运行报 `Error loading shared library libkmod.so.2` | OHOS 要求共享库 codesign | 移植 glib 配方的 `_sign_shared_libs()`（binary-sign-tool -selfSign 1） |
| 8 | xz/5.8.3 依赖触发源码重建失败 | ohpcd 上 xz/5.8.3 仅 shared=True 发布，与 CI profile 默认选项不匹配 | 改用 xz/5.6.2（发布二进制匹配） |

## 源码修改

`patches/0001-musl-compat.patch`（4 hunk，python difflib 生成标准 unified diff）：
- tools/kmod.h：musl 下声明 `extern char *program_invocation_name/short_name`（`#if !__GLIBC__ && !__ANDROID__`）
- tools/log.c：定义这两个全局并以 `__progname`（basename）初始化（constructor）
- shared/util.c：`get_current_dir_name()` 回退 `getcwd(NULL, 0)`
- meson.build：多路调用工具符号链接安装脚本 `ln --symbolic --force --relative ... || true`（toybox ln 容错）

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| zlib | 1.3.1.1.1 | gzip 压缩模块支持 |
| xz | 5.6.2 | xz 压缩模块支持（5.8.3 发布二进制不匹配，见 #8） |
| zstd | 1.5.7.1 | zstd 压缩模块支持 |
| openssl | 3.5.6 | PKCS7 模块签名校验（modinfo） |

## 上游测试（2026-09-05 实跑）

- **清点**：testsuite/ 下 16 个 `test-*.c` 可执行测试，经 `meson test` 注册（test-array/blacklist/dependencies/depmod/hash/init/initstate/list/loaded/modinfo/modprobe/new-module/strbuf/testsuite/util/weakdep）。
- **OHOS 适配整改（评审 rule 4 返工，补丁 0002-0004）**：
  1. `module-playground` 用 **stub 内核头（stub-linux/）+ 原生 clang 直编**产出 .ko（含 .modinfo/vermagic/__ksymtab_strings）——无需 Linux kbuild 树（OHOS 无内核头，已 1-e 核验）；`vermagic.h` 经 `-include` 注入修复 "Failed to strip version information: No data available"；`EXPORT_SYMBOL` 写入 `__ksymtab_strings` 段修复 `modprobe_show_exports`（实测 PASSED）。
  2. `setup-modules.sh` `cp --archive` → `cp -r`；`setup-rootfs.sh` `install -d/-t/-D` → `mkdir/cp`（toybox 无 install(1)/cp --archive）。
  3. zstd CLI 来自 zstd 包（配方 generate 注入 zstd bin 到 PATH），`zstd --rm` 可用。
  4. `testsuite/path.c` `#undef open64/fopen64/stat64`（OHOS fcntl.h 将 open64 宏映射为 open 导致重定义）；`testsuite/meson.build` 用显式 `bash` 调用 setup 脚本（无 /bin/bash）。
- **实测结果（meson test，CI profile）**：**16/16 实跑，12/16 通过，4 失败**：
  | 失败测试 | 根因（逐条证据见 CI/本地日志） |
  |---|---|
  | test-init | "module mod_simple not loaded"——LD_PRELOAD 的 init_module 模拟在 OHOS 未记录加载 |
  | test-strbuf | 上游 xfail 用例在 OHOS 不崩溃而通过（UNEXPECTED PASS）——assert 行为平台差异 |
  | test-depmod | modules.dep 输出序/内容与期望不符（压缩/outdir）+ detect_loop stderr 管道断 |
  | test-modprobe | 多数子项 "module not loaded"（加载模拟）；install_cmd_loop 超时；show_exports 已修复通过 |
- 其余 12 项（array/blacklist/dependencies/hash/initstate/loaded/modinfo/new-module/testsuite/util/weakdep 等）**实测通过**。

## 验证结果

```bash
conan create . --user=ohpcd --channel=stable -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 上游测试：16/16 实跑，12/16 通过（4 失败见上，逐条日志留档）
# test_package R34：pam_permit/IniParser 同款消费者冒烟 PASS（历史实测）
```

## 注意事项

- `package_type=library` + `cpp_info.bindirs=["bin","sbin"]`（含 CLI 工具）→ 软件级 commands.json 已建（R38）。
- libkmod 仅共享库（上游 LT_INIT disable-static），非系统同名库，故默认动态链接（R26 不适用）。
- libkmod.pc/kmod.pc 已随包安装，下游可用 pkg-config。
