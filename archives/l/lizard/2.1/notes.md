# lizard 2.1 适配笔记

## 基本信息

- issue: 待补（项目文件与当前会话未找到明确 issue 编号）
- worktree: `D:\harmonyos\worktrees\lizard`
- branch: `feat/lizard-2.1-windrel`
- source: `https://github.com/inikep/lizard/archive/refs/tags/v2.1.tar.gz`
- sha256: `0c1a7efceeb8ae66bfa2b7b659f01dec120925d846b01ce4dfc6960ba8cd61e5`
- build system: pure Makefile
- dependencies: none
- status: built（2026-07-31 真机单包 CI 通过，未 upload/published）

## W0 依赖检查

- 上游源码自带 `lib/xxhash` 与 `lib/entropy`，未发现 Conan 外部依赖。
- `ohc-run.py init-build lizard 2.1` 依赖检查结果为“所有依赖已就绪”。
- 本机未安装 `conan`，无法执行 `conan download` 或 `conan-verify`。

## 构建与配方策略

- 使用 Conan `basic_layout()` + `get(..., strip_root=True)` 解包官方 GitHub tag。
- 不调用 `make install`：上游 install 依赖 `uname` POSIX 白名单和 `install(1)`，OHOS/精简环境风险较高。
- `build()` 通过 Conan profile 的 `tools.build:compiler_executables` 取得 `CC/AR`，执行 `make -j1 -C lib` 和 `make -j1 -C programs`。
- 默认构建静态库 `liblizard.a`，仍打包 `lizard` CLI；`shared=True` 时复制 `liblizard.so*`。
- 已添加软件级 `archives/l/lizard/commands.json`，声明 `lizard` 命令行工具。
- 上游 install 公开 `lizard_common.h`，该头依赖 `entropy/mem.h`，配方同步复制到 `include/entropy/mem.h`。
- 上游完整 `make test` 包含 `test-lizard-hugefile`（6GB 流水测试），前置阶段不默认运行；配方保留较轻的 `make -C examples test`。

## 本机验证

```powershell
# 初始化源码与归档目录
$env:PYTHONIOENCODING='utf-8'; $env:SKILL_ROOT=(Get-Location).Path
python scripts/ohc-run.py init-build lizard 2.1 --url=https://github.com/inikep/lizard/archive/refs/tags/v2.1.tar.gz

# 源码校验
Get-FileHash -Algorithm SHA256 C:\Users\Windrel\tmp\builds\lizard-2.1.tar.gz

# MSYS2 本机源码探针
C:\msys64\mingw64\bin\mingw32-make.exe -j1 -C lib liblizard.a CC=gcc AR=ar
C:\msys64\mingw64\bin\mingw32-make.exe -j1 -C programs lizard CC=gcc AR=ar

# API 往返探针结果
PASS lizard version=20100 compressed=36
```

备注：Windows 根 Makefile 的 `all` 目标在最终 `cp programs/lizard.exe .` 处失败，本质是 Windows shell 缺 POSIX `cp/uname/grep`，分目录库和 CLI 构建均已通过；OHOS 侧需以真机/影子 CI 为准。

## 待真机/影子 CI 命令

2026-07-31 已在真机执行单包 CI：

```sh
CI_PACKAGES="archives/l/lizard/2.1" zsh ci/conan/build_and_test.sh archives/l/lizard/2.1
```

验证结果：

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: lizard --version OK
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
Build Summary: Total=1 Success=1 Failed=0
```

????????????? `logs/conan_lizard_2.1.log`?PR ??????????

如提交后 HEAD 变化，需要重新运行：

```sh
# 在真机隔离 job 或 CI 快照中执行
python3 scripts/ohc-run.py conan-verify lizard 2.1

# 影子 CI 定向单包，不扫描全仓
CI_PACKAGES="archives/l/lizard/2.1" zsh ci/conan/setup.sh
CI_PACKAGES="archives/l/lizard/2.1" zsh ci/conan/build_and_test.sh "archives/l/lizard/2.1"

# 若已部署 run-ohos-shadow-ci.sh
CI_PACKAGES="archives/l/lizard/2.1" sh "$HOME/bin/run-ohos-shadow-ci.sh" "$CI_PACKAGES"
```

## 阻塞点

- issue 编号待补。
- 本机缺 `conan`、`cmake`、GNU `make`，本机仍只能完成源码级和静态配方检查。
- 真机验证仓库已跑通单包 CI；PR 创建/更新前仍需补 issue 编号并确认目标 PR 编号。

## PR 模板建议

```markdown
## 变更内容
- 新增 lizard/2.1 Conan 配方、源码校验、test_package 与软件级 commands.json。
- 默认构建静态 liblizard.a，同时打包 lizard CLI；不依赖上游 make install。
- 上游轻量测试执行 make -C examples test，test_package 执行 API 往返断言。

## 质量状态
- 真机单包 CI 通过：archives/l/lizard/2.1
- L0/L1/L2/L4/L5：pass
- Build Summary：Total=1，Success=1，Failed=0

## 验证结果
上游测试用例通过率：3/3（100%，examples 代表性轻量测试）
test_package：1/1（100%，Lizard_compress + Lizard_decompress_safe 往返）
issue：待补
```
