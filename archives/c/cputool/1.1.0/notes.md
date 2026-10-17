# cputool 1.1.0 适配笔记

## 编译环境

- 构建系统：meson（单可执行文件，无 configure 脚本）
- 上游版本：1.1.0（上游仓库 https://gitlab.linux.community/cputool/cputool/）
- 源码包：cputool_1.1.0.orig.tar.xz（22792 字节，
  sha256=d92972c346c0cd249de3b4a064d2e4384ffbd5f188176b9f35b2f87282bb04f8，
  经官方 .dsc 与 Ubuntu MD5 三方交叉验证）
- 状态：首轮工作树已完成，待 HMBS 真机预检回填实测数据

## 编译步骤

cputool 使用 Meson 构建，产物为单个 `cputool` 二进制（无库目标）。

```bash
conan create archives/c/cputool/1.1.0 --profile ci/conan/profiles/ohos-aarch64
# 等价手动流程（配方实际执行）：
# meson setup build -Ddocs=disabled -Ddefault_library=static
# ninja -C build
# meson install -C build
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 顶层 meson.build 无条件 `find_program(rst2man)`，OHOS 无 python3-docutils 会导致 configure 直接失败 | 上游把文档工具查找放在 `gen_docs` 判断之前，且为必需查找 | 补丁 `0001-meson-build.patch` 将该查找改为 `required: false` 并用 `prog.found()` 守卫；配方同时传 `-Ddocs=disabled` 跳过 docs 子目录 |
| 2 | 上游归档站（linuxassist.net）已失效，Anubis 墙挡住抓取 | 上游迁移至 gitlab.linux.community，旧域名停放 | conandata 采用 Debian 官方发布包（与上游 release 同源），阿里云镜像优先、deb.debian.org 兜底，同一 sha256 校验 |

## 源码修改

| 文件 | 补丁 | 修改内容 |
|------|------|----------|
| meson.build | 0001-meson-build.patch | rst2man 查找改为 `required: false` + `prog.found()` 守卫；默认行为不变（有 rst2man 时与上游一致），缺失时 configure 不再报错 |

## 依赖版本

- 无外部依赖（仅 libc；源码仅含 POSIX 头文件，无 Linux 专有头文件）

## 上游测试审计

上游 1.1.0 无任何测试套件（详见 test_package/MANIFEST.yml）：发布包 15 个成员无
tests/ 目录与 *test* 文件；meson.build 仅有 `executable(cputool)` 无 `test()` 目标；
meson_options.txt 无测试开关；`.gitlab-ci.yml` 只有构建任务。因此配方 `build()`
不调用上游测试，test_package 复发 `no_tests` 证据标记。

## 验证结果

待 HMBS 真机预检完成后回填：

```bash
# L2 smoke test（预期）
$ cputool -V
cputool 1.1.0
$ cputool --help
cputool 1.1.0 - Copyright (c) 2012-2021, AllWorldIT
Usage: cputool [-c PCNT] [-l LOAD] [[-p PID | -P PID] | [--] COMMAND ...]
```

- test_package：test_cputool.sh 5 项内容级检查（实测通过数待回填）
- 上游测试：no_tests（上游无测试可运行）

## 注意事项

- cputool 是命令行工具，非库。conanfile.py 中 `package_type = "application"`，
  package_info 仅声明 `bindirs = ["bin"]`。
- man 手册页在 OHOS 包中缺失（docs 禁用），二进制功能不受影响。
- 运行时进程统计依赖 `/proc`，OHOS 上实时管控场景可能受限；二进制自检
  （-V/--help/参数校验）不受影响。
- `werror=true` 为上游默认予以保留；若真机出现告警转错误再行处理。
---

**笔记更新**：2026-09-11（首轮工作树；验证数据待真机预检回填）
