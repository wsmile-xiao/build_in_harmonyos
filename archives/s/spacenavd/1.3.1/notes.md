# spacenavd 1.3.1 — 适配笔记

任务：平台 10828｜档位【中】｜语言 c（37 文件）｜构建系统 handwritten-configure｜首次适配
上游：spacenavd 1.3.1（经 Debian pool orig tarball 引入）
源码：`spacenavd_1.3.1.orig.tar.gz`
sha256 见 conandata.yml（与 Debian 索引 Checksums-Sha256 一致）

## 1. 手写 configure 的注入面（零源码补丁）

上游 configure 为手写脚本（非 autoconf），但明确支持：
- `CC` 环境变量 → 写入 Makefile（`CC ?= gcc` 仅是兜底，env 注入即覆盖）；
- `CFLAGS` 环境变量 → `add_cflags` 追加进 Makefile；
- `--prefix=<path>` 与 `--disable-x11`（X11 通信模式默认开，OHOS 无 X11 必须关）。
⇒ 适配全程零源码补丁：`CFLAGS="-DHAVE_STDINT_H" CC=<clang> ./configure
--prefix=<pkg> --disable-x11 && make -j2 CC=<clang>`。

## 2. --disable-x11 揭露的被掩盖依赖

X11 模式默认开且 X11 头传递包含掩盖了 `src/proto.h` 的类型需求：禁 X11 后
`proto.h:28 unknown type name int32_t`。proto.h 本有 `#ifdef HAVE_STDINT_H`
守卫，但手写 configure 的 config.h 模板**不做 stdint 探测**（非 autoconf 无
AC_CHECK_HEADERS）⇒ 配方注入 `CFLAGS=-DHAVE_STDINT_H` 即可，proto.h 的守卫
随之生效。XInput2/XTest 特性同样自动关闭（OHOS 无 X11 头）。

## 3. 功能实测（五维账本）

| 维度 | 读数 |
|---|---|
| 上游静态注册 N_static | **0**（上游无任何测试目标） |
| 本环境注册/执行 | 0 / 0 |
| 通过 | 0 |
| 未执行 | 0（无注册即无未执行） |
| 消费者 | **1 程序 / 4 组断言**，4/4 PASS |

消费者断言（test_package/test_spnavd.sh，真实执行打包产物）：①PATH 解析；
②`-V` 输出 1.3.1 且 rc=0；③`-h` 输出 usage；④非法选项 `-Z` 拒绝（rc≠0）。
**能力边界（诚实声明）**：守护主循环需要 /dev/input/event 真实空标鼠设备并
涉及输入设备权限，属硬件权限面——不启动设备循环，未纳入断言。

## 4. B 判定

- **none（理由）**：本包全部落点均为上游自带的开关/env 注入面（configure 原生
  支持 CC/CFLAGS/--disable-x11/--prefix），无源码补丁、无新增 OHOS 专属机制；
  手写 configure 的 config.h 不探测 stdint 一点，量级不足以独立成条（对比
  M12"自研 configure 只认命令行"是相反方向），留 notes 检索即可。若 CI/AI
  环节撞出新机制再补 create/hit 判定。

## 5. CI 取源风险预声明

源 URL = deb.debian.org（CI 镜像改写仅覆盖 github.com 域，本包直接拉取）；
sha256 双向核对（实测 + Debian 索引），E299 类 404-HTML 伪装由 sha256 硬闸兜底。
---

**编译结束**: 2026-09-25 07:40
**最终状态**: built
