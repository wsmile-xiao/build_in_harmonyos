# sd-tools 0.99.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-06-08
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 解压源码到 ~/builds/sd-tools-0.99.0.work
2. 配置 meson: `meson setup build --prefix=$HOME/usr/local -Dtests=false -Dacl=disabled`
3. 编译: `ninja -C build`
4. 安装到 staging: `DESTDIR=$HOME/test-install-sd-tools-0.99.0 ninja install`
5. 安装到本地: `ninja install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | fgetpwent/fgetgrent 未定义 | musl libc 不支持这些 glibc 扩展函数 | 在 missing.h 中实现替代版本 |
| 2 | putpwent/putgrent/putspent/fgetspent 未定义 | musl libc 不支持这些 glibc 扩展函数 | 在 missing.h 中实现替代版本 |
| 3 | cap_t 等类型未定义 | libcap 头文件路径未包含在编译参数中 | 在 meson.build 中添加 include 路径 |
| 4 | libcap 链接失败 (-lcap 未找到) | libcap.pc 中 libdir 路径错误 | 修复 libcap.pc 文件，将 libdir 改为正确路径 |
| 5 | program_invocation_short_name 未定义 | glibc 扩展宏，musl 不支持 | 在 missing.h 中定义宏 |

## 源码修改

生成了 10 个补丁文件：
- 0001-meson.build.patch: 添加 libcap include 路径
- 0002-src-shared-btrfs-util.c.patch: 包含 missing.h
- 0003-src-shared-copy.c.patch: 包含 missing.h
- 0004-src-shared-fs-util.c.patch: 包含 missing.h
- 0005-src-shared-path-util.c.patch: 包含 missing.h
- 0006-src-shared-rm-rf.c.patch: 包含 missing.h
- 0007-src-shared-strv.c.patch: 包含 missing.h
- 0008-src-sysusers-sysusers.c.patch: 包含 missing.h
- 0009-src-tmpfiles-offline-passwd.c.patch: 包含 missing.h
- 0010-src-tmpfiles-tmpfiles.c.patch: 包含 missing.h

主要修改：
- src/shared/missing.h: 添加 musl libc 缺失函数的实现（fgetpwent, fgetgrent, fgetspent, putpwent, putgrent, putspent, reallocarray, secure_getenv, get_current_dir_name, program_invocation_short_name）

## 依赖版本

- libcap/2.69（运行时依赖）

## 验证结果

```bash
$ sd-sysusers --version
sd-tools 0.99.0

$ sd-tmpfiles --version
sd-tools 0.99.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sd-sysusers | 596KB | 用户/组管理工具 |
| sd-tmpfiles | 748KB | 临时文件管理工具 |

## 注意事项

1. sd-tools 使用 meson 构建系统，而非 autotools（manifest.yaml 已更新）
2. libcap.pc 文件中的 libdir 路径错误，需要手动修复
3. G0 干净构建验证失败，因为脚本使用 autotools configure 命令而非 meson setup
4. 预编译包未生成，因为质量门禁验证失败（需要修复 G0 验证流程）

---
**编译结束**: 2026-06-08 16:25
**最终状态**: built
---

**编译结束**: 2026-06-08 16:47
**最终状态**: built
