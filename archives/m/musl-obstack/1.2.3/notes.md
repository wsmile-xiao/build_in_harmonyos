# musl-obstack 1.2.3 编译进度

**日期**: 2026-04-21
**状态**: 🔄 编译中

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ⏳ | |
| Step 2 patches | ⏳ | |
| Step 3 configure | ⏳ | |
| Step 4 make | ⏳ | |
| Step 5 install | ⏳ | |
| Step 6 safety | ⏳ | |
| Step 7 check | ⏳ | |
| Step 8 staging | ⏳ | |
| Step 9 package | ⏳ | |
| Step 10 deploy | ⏳ | |
| Step 11 finish | ⏳ | |

## 发现与知识

<!-- 编译过程中发现的问题和解决方案 -->

---

**编译结束**: 2026-04-21 20:15
**最终状态**: partial

---

# Conan 配方补充（2026-07-30）

> 以上为 2026-04 手工编译路径的原始记录，**原样保留**。以下为本次新增的 Conan 配方说明。

# musl-obstack 1.2.3 —— Conan 配方补充说明

## 与上面 2026-04 手工路径的关系
前人的手工编译记录**完整保留在上方**，本次是补 Conan 配方。

## 定位
musl 不提供 glibc 的 `obstack`（可增长对象栈），elfutils 等库需要它。本包补齐。

## 关键适配
- 显式三元组 `--build/--host=aarch64-unknown-linux-musl`，跳过 `config.guess`。

## 状态
built —— 真机 `conan create` 通过；test_package 真实使用
`obstack_init`/`obstack_alloc`/`obstack_free` 分配并断言内容，非仅链接成功。
