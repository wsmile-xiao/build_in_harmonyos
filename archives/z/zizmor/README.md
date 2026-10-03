# zizmor

`zizmor` — GitHub Actions 工作流静态安全分析工具（"Static analysis for GitHub
Actions"）：审计 `.github/workflows/*.yml`、action 定义与 dependabot 配置中的
安全问题（未固定（unpinned）的 action 引用、模板注入、缓存投毒、过宽权限、
凭据持久化等 40+ 审计项）。

- 上游仓库：<https://github.com/zizmorcore/zizmor>
- 官方文档：<https://docs.zizmor.sh>
- 适配版本：`1.27.0`（GitHub tag `v1.27.0`；该版本未发布到 crates.io）

## HarmonyOS PC 适配要点

产物为 `aarch64-unknown-linux-ohos` 的 CLI 可执行文件（`bin/zizmor`）。

1. **工具链**：`tool_requires("rust-toolchain/1.97.1")`（制品仓基础设施包，
   含 `aarch64-unknown-linux-ohos` 标准库）。Conan 包内 ELF 无执行位，构建期
   复制 cargo/rustc 到私有目录并在必要时用 OHOS `binary-sign-tool` 自签名。
2. **cargo 运行期共享库**：cargo 1.97 动态链接 libssl/libcrypto/libz，使用
   Harmonybrew OHOS bottle（sha256 固定）注入 `LD_LIBRARY_PATH`，不写共享前缀。
3. **jemalloc 排除**（`patches/0001`）：jemalloc 的线程缓存/TSD 析构路径在
   HarmonyOS 上 SIGSEGV，故 `target_env = "ohos"` 使用平台分配器。修复前
   zizmor 审计路径 10/10 崩溃、单元测试 93/148 崩溃；修复后全绿。
4. **aws-lc CMake 平台修正**：配方注入最小 `CMAKE_TOOLCHAIN_FILE`
   （`CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`），使 aws-lc
   选用 `generated-src/linux-aarch64` 汇编实现（否则链接期 asm 符号未定义）。
5. **`.git` 标记**：上游集成快照 `e2e::issue_1745` 依赖源码树是 Git 工作树，
   tarball 构建时由 `build()` 补 `.git` 目录。

## 验证结果（本机真机 / HarmonyOS PC，aarch64-unknown-linux-ohos）

| 项 | 结果 |
|---|---|
| 上游测试（cargo，15 个测试二进制） | **562 passed / 0 failed / 35 ignored** |
| test_package（含 3 项鸿蒙特有用例） | 8/8 passed |
| conan create / conan-verify | 通过（详见 `1.27.0/reports/`） |

上游门控用例说明：`gh-token-tests`（21 例，需 GH_TOKEN + GitHub API）、
`tty-tests`（需 expect/unbuffer）、`crater-tests`（需联网克隆仓库）在本机与
CI worker 均不具备前置条件；doctests 因 `rust-toolchain/1.97.1` 不含 rustdoc
而无法执行。
