# callaudiocli 0.1.10 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. 下载 callaudiod 0.1.10 源码 (GitLab)
2. 安装系统依赖: glib 2.88.0, alsa-lib 1.2.12, pcre2 10.40, libffi 3.4.4 (cmd-pkgs)
3. 修改 meson.build: 将 callaudiod 守护进程(src/)设为条件构建
   - 守护进程需要 PulseAudio 和 ALSA
   - 在 HarmonyOS 上 PulseAudio 不可用，跳过守护进程
   - callaudiocli CLI 工具和 libcallaudio 库仍正常构建
4. 运行 meson setup + ninja 编译
5. 运行 meson install --destdir 安装到 staging 目录

```bash
meson setup builddir --prefix=$DEFAULT_PREFIX --buildtype=debugoptimized -Dgtk_doc=false
ninja -C builddir -j2
meson install -C builddir --destdir=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libffi.so 损坏 (10KB vs 120KB) | cmd-pkgs 安装的 libffi.so 文件截断 | 从系统 HNP 目录 /data/service/hnp/libffi.org/libffi_3.4.4/ 复制正确的 .so 文件 |
| 2 | PulseAudio 不可用 | 制品仓和 cmd-pkgs 均无 pulseaudio | 修改 meson.build 使守护进程构建条件化，仅构建 CLI 工具和库 |
| 3 | meson 找不到 clang/llvm-ar | PATH 在子进程中未正确继承 | 使用 meson --native-file 指定完整编译器路径 |

## 源码修改

- 0001-meson.build.patch: 将 subdir('src') 改为条件构建，当 PulseAudio/ALSA 不可用时跳过守护进程

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| glib | 2.84.0 | conan 制品仓 (glib/2.84.0) |
| glib (system) | 2.88.0 | cmd-pkgs 预编译包 |
| alsa-lib | 1.2.12 | cmd-pkgs 预编译包 |
| pcre2 | 10.40 | cmd-pkgs 预编译包 |
| libffi | 3.4.4 | cmd-pkgs / 系统 HNP |

## 验证结果

```bash
# ELF 链接验证
llvm-readelf -d callaudiocli
# NEEDED: libcallaudio-0.1.so.0, libpcre2-8.so.0, libffi.so.8, libz.so, libc.so

llvm-readelf -d libcallaudio-0.1.so.0
# NEEDED: libpcre2-8.so.0, libffi.so.8, libz.so, libc.so
```

## 注意事项

- callaudiocli 二进制在本地无法执行 (Operation not permitted)，需要 ELF 签名
- 守护进程 (callaudiod) 未构建，因为 PulseAudio 不可用
- libcallaudio 作为共享库构建 (shared=true)
---

**编译结束**: 2026-08-06
**最终状态**: built
