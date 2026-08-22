# rhash 1.4.6 前置适配记录

## 本轮范围

- worktree: `D:/harmonyos/worktrees/rhash`
- branch: `feat/rhash-1.4.6`
- 上游源码: `https://github.com/rhash/RHash/archive/refs/tags/v1.4.6.tar.gz`
- SHA-256: `9f6019cfeeae8ace7067ad22da4e4f857bb2cfa6c2deaa2258f55b2227ec937a`

## W0 依赖检查

OpenSSL 在 RHash 中是可选的优化哈希实现，RHash 自带所有受支持算法的内部实现，并非依赖 OpenSSL 才提供算法或 TLS 功能。配方显式关闭 OpenSSL 自动探测，避免静态包因 Worker 环境差异产生未声明的 `libcrypto` 链接依赖；上游 CLI、静态库算法测试和 Conan 消费者测试均已覆盖禁用后的功能。

配方同时关闭 gettext 和共享库，仅构建自包含的 LibRHash 静态库与 `rhash` CLI，因此没有需要拆分的外部依赖。真机发布前仍应在 OHOS Conan 环境执行：

```sh
conan download "rhash/1.4.6" -r=ohpcd --only-recipe
```

## 源码与构建分析

RHash v1.4.6 是 `configure` + Makefile 项目。配方使用 `CONFIG_SHELL`，从 `tools.build:compiler_executables` 获取 C 编译器和归档器，固定 `make -j1`，并在 `build()` 中执行上游 `make -j1 test test-lib`。HMDFS 场景禁用共享库和符号链接；安装阶段直接复制 `librhash.a`、两个公开头文件和 `rhash`。

## Conan 与消费者测试

`test_package` 通过 CMakeDeps 链接 `rhash::rhash`，实际调用 `rhash_library_init()`, `rhash_count()`, `rhash_msg()`, `rhash_get_digest_size()` 和 `rhash_print_bytes()`，校验 MD5("hello") 与 SHA1("message digest")。

## 本机验证

- `python -m py_compile`：主配方和 test_package 配方通过。
- `git diff --check`：通过。
- Windows 主机未安装 Conan/clang/make/cmake，因此真实编译转由 OHOS aarch64 shadow CI 完成。
- 源码归档 SHA-256 与上游发布信息一致。

## 真机 / shadow CI 结果

正式 run：

```text
/storage/Users/currentUser/ohpc-ci-shadow/runs/f3c15f87eafc-20260820T125700Z-run-2245
```

验证结果：

- `make -j1 test`：上游 25 项 CLI 测试全部通过。
- `make -j1 test-lib`：静态库算法测试通过。
- Conan `test_package`：输出 `PASS: MD5/SHA1 API checks`。
- L0/L1/L2/L4/L5：全部通过。
- Build Summary：Total 1，Success 1，Failed 0。
- 环境：HarmonyOS aarch64、clang 15.0.4、Conan 2.29.1。

PR CI 复验：

- 首次 PR CI #28819 在 Worker 031 的 configure 编译器探测阶段失败；同一提交切换 Worker 重跑后，PR CI #28842（Worker 038）通过。
- #28842 中 L0/R38 `commands.json`、L0 全部门禁、Conan `test_package`、L1 和 `conan-build-test` 全部通过。

## 知识草稿

- `knowledge/drafts/E321-draft-RH46.kv`
- `knowledge/drafts/E321-draft-RH46.md`
- 内容按标准知识图谱格式记录可选加速后端在静态包中的显式依赖策略，并以 RHash 1.4.6 的 OpenSSL 决策和真机测试为证据。

## 阻塞点

无。没有需要先行适配的依赖库，也没有修改基础设施目录。
