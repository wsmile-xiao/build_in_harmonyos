# GMP 6.3.0 OpenHarmony/HarmonyOS 适配笔记

## 编译环境

- 目标平台: OpenHarmony/HarmonyOS PC arm64
- Conan settings: `os=OHOS`, `os.version=6.0`, `arch=armv8`
- 构建系统: Autotools
- 编译器: clang 15.0.4
- 构建类型: 静态 PIC 库
- 源码 SHA256: `a3c2b80201b89e68616f4ad30bc66aee4927c3ce50e33929ca819d5c43538898`
- 状态: `built`

## 构建配置

```text
--disable-shared
--enable-static
--with-pic
ABI=64
```

`--with-pic` 是下游 GnuCOBOL 的必要条件：`libgmp.a` 会链接到共享 `libcob.so`，非 PIC 静态对象会触发 AArch64 relocation 错误。

## 平台适配

| 补丁 | 问题 | 处理 |
|---|---|---|
| `0001-configfsf.guess.patch` | `configfsf.guess` 不识别 HarmonyOS | 返回 `aarch64-unknown-linux-ohos` |
| `0002-configfsf.sub.patch` | `configfsf.sub` 拒绝 `linux-ohos` | 接受 OHOS triplet 和 kernel/OS 组合 |
| `0003-configure.patch` | HMDFS 上 `umask 077` 创建的 `config.status` 临时目录不可写 | 使用 `$TMPDIR` 并移除不兼容的 umask |

HMDFS 不支持 libtool 尝试创建的硬链接。libtool 会自动回退到复制对象文件，该警告不影响最终静态库。

## 验证结果

- `conan-verify gmp 6.3.0`: PASS
- Conan 干净构建: PASS
- 上游 `make check`: PASS
- test_package 真实调用 `mpz_init_set_ui`、`mpz_mul_ui`、`mpz_cmp_ui` 和 `gmp_printf`: PASS
- 安装后的 `libgmp.a` 链接进 AArch64 共享对象探针: PASS
- 制品: `lib/libgmp.a` 1,093,896 bytes、`include/gmp.h`、`lib/pkgconfig/gmp.pc`

## 状态说明

GMP 配方和本地 OHOS arm64 包已完整验证，但尚未发布到远端 `ohpcd` 制品仓。GnuCOBOL 发布前必须先合并并发布 GMP，以满足 R36。
---

**编译结束**: 2026-07-15 10:42
**最终状态**: built
