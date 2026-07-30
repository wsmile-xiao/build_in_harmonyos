# musl-fts latest 编译进度

**日期**: 2026-04-21
**状态**: ✅ 编译完成

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | URL: https://github.com/void-linux/musl-fts/archive/refs/tags/v1.2.7.tar.gz |
| Step 2 patches | ✅ | 修改 configure.ac 和 Makefile.am |
| Step 3 configure | ✅ | 需修补 config.status 绕过 HMDFS mktemp 权限问题 (E011) |
| Step 4 make | ✅ | 一次性通过 |
| Step 5 install | ✅ | DESTDIR staging + 本地安装 |
| Step 6 safety | ✅ | 无二进制可执行文件（仅库） |
| Step 7 check | ⏭️ | 无测试套件 |
| Step 8 staging | ✅ | lib/libfts.so.0.0.0, lib/libfts.a, include/fts.h, lib/pkgconfig/musl-fts.pc |
| Step 9 package | ✅ | musl-fts-latest-ohos-aarch64.tar.gz (102KB) |
| Step 10 deploy | ✅ | 已安装到 ~/usr/local |
| Step 11 finish | ✅ | partial |

## 发现与知识

✅ extracted: E080 draft (L2) — aclocal @am_AUTOM4TE@ 未替换导致 PKG_INSTALLDIR 缺失
✅ extracted: E011 (L1) — HMDFS mktemp 权限问题
✅ extracted: 平台限制 (L1) — HMDFS 符号链接复制权限

**编译结束**: 2026-04-21 19:54
**最终状态**: partial

---

**编译结束**: 2026-04-21 20:00
**最终状态**: partial

---

# Conan 配方补充（2026-07-30）

> 以上为 2026-04 手工编译路径的原始记录，**原样保留**。以下为本次新增的 Conan 配方说明。

# musl-fts 1.2.7 —— Conan 配方补充说明

## 与上面 2026-04 手工路径的关系
前人的手工编译记录**完整保留在上方**，本次是补 Conan 配方。

## 定位
musl 不提供 BSD 的 `fts(3)` 系列，elfutils 等库需要它。本包补齐该接口。

## 关键适配
- 显式三元组 `--build/--host=aarch64-unknown-linux-musl`，跳过 `config.guess`。
- **测试临时目录必须建在 CWD**：test_package 起初用 `/tmp`，
  在 HarmonyOS 沙箱下 `mkdtemp` 失败（`/tmp` 不可写）。

## 状态
built —— 真机 `conan create` 通过；test_package 真实建目录树并用 `fts_open`/`fts_read`
遍历、断言遍历到的条目数，非仅链接成功。
