# libucontext 1.5.2 适配笔记

## 最终状态
- 状态: published（编译结束标记）
- 分支: feat/libucontext-1.5.2
- 提交: 已通过 W4 审计，准备提交 PR

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-18
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: published（Conan 配方已通过全部门禁）

## 编译步骤

1. 源码：GitHub tag `libucontext-1.5.2`（`https://github.com/kaniini/libucontext/archive/refs/tags/libucontext-1.5.2.tar.gz`，sha256 `9230397327...`）。
2. 构建：`make ARCH=aarch64 CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j1 all`。
3. 上游测试：`make check` → 3 个测试程序全部通过（`test_libucontext` / `test_libucontext_bare_posixabi` / `test_libucontext_posix`，exit 0）。
4. Conan 配方：`conan-init` 生成，AI 改写为真实 makefile 配方。
5. 验证：`conan create`（含 test_package 上游测试）→ 100% 通过；`conan-verify` 8 道门禁全部 PASS。
6. 收尾：`finish published` → W2 结构 ✅ / W3 conan create（.ci-result.json）✅ / submit 就绪 ✅。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 包内无产物（CMakeDeps 找不到 `ucontext` 库） | 1.5.2 Makefile 改用 `prefix/libdir` 变量体系（默认 /usr），1.2 的 `LIBDIR=lib` 参数被忽略 | 安装时传 `prefix=` 空值 + DESTDIR，产物落到包内 /lib |

## 源码修改

无（libucontext aarch64 为 tier-1 支持，纯 makefile 构建，无需补丁）。

## 依赖版本

无第三方运行时依赖（纯汇编 + C 实现）。

## 验证结果

```text
make check: 3/3 套件通过（exit 0）
conan create 测试: 100% tests passed (1/1)
conan-verify: G0-G4 + L2/L4/L5 全部 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | Conan makefile 配方（含上游 make check + 静态隔离） |
| `conandata.yml` | 官方源 + sha256 |
| `test_package/` | 消费者测试（复用上游 test_libucontext.c）+ MANIFEST.yml |

## 注意事项

- OHOS musl libc 不导出 `getcontext`/`setcontext`，libucontext 是 accel-ppp 等需要 ucontext 的软件的必要依赖。
- 上游仓库官方 tag 为 `libucontext-1.5.2`（注意前缀 `libucontext-`）。
- 1.2 已被 PR #1220 合并，本版本选择 1.5.2 避免重复适配。
---

**编译结束**: 2026-08-19 02:47
**最终状态**: published
