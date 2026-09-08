# uusi 0.4.4.0 适配笔记

## 上游信息
- 主页: https://github.com/berberman/uusi
- Hackage: https://hackage.haskell.org/package/uusi
- 源码包: https://hackage.haskell.org/package/uusi-0.4.4.0/uusi-0.4.4.0.tar.gz
- 许可证: MIT

## 构建系统分析
- Haskell / Cabal `build-type: Simple`
- 入口文件: `Setup.hs`
- 可执行文件: `uusi`、`gen-setup`、`uusi-extract`
- 测试套件: `uusi-tests`（HUnit）

## W0 依赖检查
- Conan 依赖: 无
- 构建时 Haskell 库依赖都在 GHC 工具链里
- 本机起初未安装可用 GHC；已补齐本机 GHC 9.14.1，用于继续做前置验证

## 适配方案
1. 用 harmonybrew 提供 GHC
2. `ghc --make Setup.hs -o Setup`
3. `Setup configure --prefix=/usr --enable-executable-static --enable-tests`
4. `Setup build`
5. `Setup test --show-details=direct` 实跑上游 `uusi-tests`
6. package() 直接拷贝三个未剥符号的 dist 二进制
7. test_package 用样例 `.cabal` 文件验证 `uusi-extract`、`uusi`、`gen-setup`

## 本机验证
- 已验证 tarball 顶层目录为 `uusi-0.4.4.0/`
- 已验证 `uusi.cabal` 结构与 CLI 源码
- 已计算源码包 SHA256
- 已补齐本机 GHC 工具链；`conan create` 和 `test_package` 已在真机跑通
- 已用 `ghci` 走到 `Setup.hs configure`，并确认需要显式传入 `--with-compiler` / `--with-hc-pkg`
- 审查整改后补齐 `Test.HUnit` package-local 兼容模块并启用 `uusi-tests`，上游 5 个 HUnit 用例由 `Setup test --show-details=direct` 执行

## 知识草稿
- `knowledge_drafts/DRAFT-uusi-setup-hs-bootstrap.md`：Simple Cabal 包的 `Setup.hs` 两段式引导
- `knowledge_drafts/DRAFT-uusi-ghc-runtime-tree.md`：复制出来的 GHC 运行时树必须包含 `settings`、`package.conf.d` 和 libdir 目录
- `knowledge_drafts/DRAFT-uusi-ghc-toolchain-path.md`：GHC 调起 OHOS 工具链时需要 `/data/service/hnp/bin` 在 PATH 前列
- `knowledge_drafts/DRAFT-uusi-conan-os-version-cleanup.md`：Conan 2 下 recipe / test_package 都要清理 `os.version`
- `knowledge_drafts/DRAFT-uusi-test-package-contract.md`：`test_package` 需要覆盖三个可执行文件的真实语义
- `knowledge_drafts/DRAFT-uusi-hunit-shim-upstream-tests.md`：用最小 HUnit 兼容层实跑上游 `uusi-tests`

## 阻塞点
- 无

## 真机检查
- 已通过 SSH 连到真机 `10.62.220.52:2222`，确认 `conan` / `python3` 可用，但 `ghc` / `cabal` 未在 PATH 中
- 已手动把 Harmonybrew 的 portable Ruby 落到 `Library/Homebrew/vendor/portable-ruby/current`
- Homebrew 还卡在自身 vendored gem / startup 依赖链上，`brew search ghc` 尚未打通到公式查询阶段

## 真机 GHC 结论
- `ghc` / `ghc-pkg` 的 Cellar 包装脚本可以启动，但其 ELF 主体在这台设备上直接从 Cellar 路径执行会被拦
- 把可执行体复制到 `tmp/codex-bin`，并补上 `LD_LIBRARY_PATH` 后，`ghc --version` 与 `ghc-pkg --version` 都已在真机跑通
- 共享库依赖实际落在 `usr/local/lib`（`libgmp.so.10`、`libffi.so.8`）和临时整理出的 `ncurses` lib 目录
- 已补齐 `settings`、`package.conf.d` 和 `aarch64-linux-ghc-9.14.1-7fac` 的落点，`Setup.hs` 编译、`Setup build`、`conan create` 和 `test_package` 都已通过
- 真机侧额外需要把 `/data/service/hnp/bin` 放进 PATH，让 `clang` / `ld.lld` / `ar` 可被 GHC 调起
- PR CI #40535 新装 harmonybrew GHC 后，`Setup` 动态加载不到 `libgmp.so.10` / `libffi.so.8`；recipe 已在 Haskell 构建阶段统一补齐 harmonybrew `gmp`、`libffi`、`ncurses` 和 GHC libdir 到 `LD_LIBRARY_PATH` / `LIBRARY_PATH`

## 审查整改
- PR 审查指出 `uusi-tests` 存在但旧版 recipe 未执行上游测试，不符合上游测试规则
- HUnit 是独立 Haskell 测试依赖，按“一库一 PR”约束不能把完整 HUnit 适配混入本 PR
- 上游 `test/Main.hs` 仅依赖 `Test.HUnit` 的 `Test`、`test`、`(~:)`、`(~=?)`、`runTestTTAndExit`；已通过 `patches/0001-enable-upstream-tests-with-hunit-shim.patch` 提供等价最小实现，并保持原测试断言逻辑不变
- PR CI #40576 进入 `uusi-tests` 编译后发现 Haskell2010 不接受 export list 尾逗号；已修正兼容模块导出列表
- PR CI #40584 继续定位到 patch 新文件 hunk 行数过短，导致 `Test.HUnit` 被截断在 `then pure ()`；已把 hunk 行数修正为 62 行
- PR 审查指出 `conandata.yml` 存在本机兜底源；已删除本地路径，仅保留 Hackage 官方源码 URL，并复核官方 tarball SHA256 不变
- PR 审查指出 `test_package/test_uusi.sh` 头部与 Conan 缓存 fallback 不规范；已改为 POSIX `set -eu`，移除 `pipefail`，并按 `CONAN_HOME`、`~/.cache/conan2/p`、`~/.conan2/p` 顺序查找安装产物
- PR 描述曾沿用早期未统计上游测试的说明；本轮需同步为上游 `uusi-tests` 5/5 通过，避免规则 4 条件 3 少报
