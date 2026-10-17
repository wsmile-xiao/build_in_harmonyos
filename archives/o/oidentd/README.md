# oidentd - HarmonyOS 编译记录

## 概述

oidentd 是 RFC 1413 (Ident) 协议的守护进程实现，监听 113/TCP，为 IRC、
邮件等服务提供客户端连接的身份查询。支持按用户/地址的细粒度配置、转发、
masquerading 与 NAT 场景。上游仓库：<https://github.com/janikrabe/oidentd>

## 已适配版本

| 版本 | 状态 | 编译日期 | 产物 |
|------|------|----------|------|
| 3.1.0 | ✅ built | 2026-09-26 | `bin/oidentd` + 配置文件 + man 页 |

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS PC (aarch64) |
| 编译器 | clang 15.0.4 |
| C 库 | musl libc |
| 三元组 | aarch64-linux-ohos |
| 构建系统 | Autotools + Conan 2.29.1 |

## 编译步骤

```bash
# 配方目录
conan create archives/o/oidentd/3.1.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

## 产物

- `bin/oidentd`（守护进程；上游安装目标为 `sbin_PROGRAMS`，经配方映射至 `bin/`）
- `etc/oidentd.conf`、`etc/oidentd_masq.conf`（默认配置模板）
- `share/man/man8/oidentd.8`、`share/man/man5/oidentd.conf.5`、`share/man/man5/oidentd_masq.conf.5`

## 关键适配点

1. 源固定为上游 release asset：内含预生成的 `configure`/`config.sub`/`install-sh`
   与 flex/bison 产物（`src/cfg_scan.c`、`src/cfg_parse.c`），因此不需要
   autoreconf/automake/libtool 自举；git tag tarball 不含 `configure`，不可替代。
2. 可选特性全关（`--disable-masq --disable-nat --disable-libnfct`）：configure.ac
   中 `masq_support=no` 会进一步归约 `want_libnfct=no`，故完全不链接
   libnetfilter_conntrack，实现 **0 运行时依赖**。
3. `config.sub`（GNU config 2018-02-24）不识别 HarmonyOS：以补丁 0001 扩展
   `maybe_os` 内核-OS 组合列表与 OS 接受列表（纯三元组列表扩展，不引入
   `#ifdef __OHOS__` 平台条件宏）。
4. AutotoolsToolchain 不自行推导 OHOS 三元组（profile 未设
   `tools.gnu:host_triplet`）→ 显式传 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`。
5. configure 的 `AC_PROG_LEX`/`AC_PROG_YACC` 为硬性探测，缺失即报错 →
   `tool_requires` flex/2.6.4 + bison/3.8.2。
6. `os.c` 由 configure 在源码树内按 `$host_os` 从 `src/kernel/<os>.c` 复制生成
   （以 `$srcdir` 相对路径写回 `src/os.c`）→ 必须 in-source 构建。
7. 上游 `sbin_PROGRAMS = oidentd`，经 Conan 的 `--sbindir=${prefix}/<首个 bindir>`
   映射落到 `bin/`，与 `package_type = "application"` 默认 `bindirs=["bin"]` 一致，
   不需要手工 `sbin/ → bin/` 折叠。

## 测试

上游未提供自动化测试套件（树内无 `make check`/testsuite/ctest 目标）。
验证采用 `test_package`：运行已安装的 `oidentd -v`，断言版本横幅
`oidentd 3.1.0`、`Build information:` 详细块与 `Kernel driver: linux`，
以证明二进制可在 OHOS 运行时启动且特性开关已抵达 `config.h`。
详见版本目录下 `notes.md` 与 `reports/test-report.md`。

## 仓库

<https://github.com/janikrabe/oidentd>
