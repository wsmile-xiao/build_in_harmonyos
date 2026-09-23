# lib25519 0-20260614 — HarmonyOS PC (OHOS aarch64) Conan 适配

## 上游

- 官方主页: <https://lib25519.cr.yp.to>
- 版本: 20260614（Conan 版本 0-20260614，Debian 风格快照版本号）
- 源码 tarball: <https://lib25519.cr.yp.to/lib25519-20260614.tar.gz>
- SHA256: `208f883405ac0c2f503c3f7d07f0e525d0b3b6f7a883ebf53d936a82840652a9`
- License: 公共领域多选一（LicenseRef-PD-hp / CC0-1.0 / 0BSD / MIT-0 / MIT），配方取 `MIT`
- 构建系统: `./configure`（python3 脚本）+ `scripts-build/` + Makefile（djb 家族）

## 包信息

Conan 2 recipe，面向 HarmonyOS PC（aarch64-unknown-linux-ohos / musl）。

| | |
|---|---|
| 聚合位置 | `archives/l/lib25519/` |
| 版本目录 | `archives/l/lib25519/0-20260614/` |
| 上游测试 | 正式套件：`command/lib25519-test`，13 个 `api` 操作分支 |
| patch 数 | 0（`helpers/` 为新增补齐文件，非上游 patch） |
| 本包 test_package | 1 个 suite（10 断言，消费者 API 契约测试） |

## OHOS 适配要点

1. **零 patch**：上游 20260614 在 OHOS aarch64 上无需任何源码修改。

2. **工具链注入**（同族 libcpucycles 模式）：上游 `./configure` 不读任何环境变量，
   编译器唯一来源是源码树 `compilers/default`。配方把 profile 配置的 OHOS clang
   前置为首行（含构建期 `-I/-L`），上游原候选行保留作 fallback；只改构建缓存副本。

3. **缺失依赖低成本补齐**：`librandombytes` 尚未入仓。配方用
   `helpers/randombytes.{h,c}`（OHOS `getrandom(2)` + `/dev/urandom` 回退，
   失败 abort）作构建期私有静态归档满足链接；shared 产物静态嵌入，
   不产生外部 DT_NEEDED；static 消费者随源码编译同文件即可。

4. **跳过 make install**：与 libcpucycles 同因（hmfs setgid 目录内临时目录 EACCES），
   直接收集 `build/arm64/package/`（install 无编译动作，语义等价）。

5. **上游测试真实运行**：`build()` 中逐个运行 13 个 `api` 操作分支的
   `lib25519-test`，每分支要求 `all tests succeeded` 且退出码 0；
   valgrind 数据流分支因 OHOS 无 valgrind 跳过（`--no-valgrind`，已声明）。

6. **musl 兼容**：ifunc 不可用时上游自动降级为 constructor 分发，无需干预。

## 验证状态（待 HMBS 真机预检回填）

- [ ] `conan create` 编译成功（OHOS aarch64, clang 15）
- [ ] 13/13 上游分支通过（含 `HMBS_UPSTREAM_TEST_RESULT` 标记）
- [ ] test_package 10/10 通过（含 `HMBS_TEST_PACKAGE_RESULT` 标记）
- [ ] ELF64 / AArch64 / interpreter `/lib/ld-musl-aarch64.so.1`

更多适配细节见 `notes.md`。
