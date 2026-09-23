# DRAFT-nut-autotools-ohos-upstream-check-chain - NUT 2.8.5 的 OHOS Autotools 上游测试闭环

> 状态：VERIFIED DRAFT
>
> 本条目是路径 B（贡献创新）候选，不预占正式 E 编号，也不宣称已经
> 通过主编或赛事评审。来源为 `archives/n/nut/2.8.5` 的真实 HarmonyOS
> Shadow CI 适配过程。

## 1. 新增知识与适用范围

NUT 2.8.5 是带预生成 Autoconf 2.71 文件的传统 Autotools 软件。它的
`configure`、顶层文档规则、`docs/man` 规则、测试源链接规则和 `data`
校验规则分别携带了不同的传统 Linux 假设。单独修复 `config.guess` 或
让 `configure` 成功，并不能说明 OHOS 上的 `make check` 已经真正执行。

本条目的新增点不是重复申报以下已有单点知识：

- E007：`config.guess/config.sub` 识别 HarmonyOS；
- E011：HMDFS 下 configure 临时目录与 umask；
- E018/E079：HMDFS 软链接/硬链接限制；
- E093：musl/OHOS 缺少 `getpass()`。

本条目沉淀的是一个可迁移的**多层 Autotools 测试闭环**：把生成的
Makefile 变量、递归测试规则、OHOS HNP 工具环境、Conan 包实际布局和
消费者断言放进同一个逐层收敛流程，并用真机 `make check` 证实不是
“只编译不测试”。

适用范围：

- 发布包已经包含 `configure`/`Makefile.in` 的旧式 Autotools C/C++ 库；
- 构建目录位于 OHOS/HMDFS，且上游测试会生成脚本、文档链接或临时文件；
- CI profile 通过绝对路径提供编译器，但不保证所有构建期工具都在
  `PATH`；
- 需要同时交付上游测试证据和 Conan `test_package` 消费者证据。

## 2. 实际失败链与诊断边界

NUT 2.8.5 的真机 Shadow CI 按失败顺序暴露了完整闭环：

| 运行 | 首个问题 | 结论 |
|---|---|---|
| `40813` | `docs/man` 规则硬编码 `ln -fs` | `configure` 选择的 `LN_S` 没有传递到手写规则 |
| `50315` | 顶层 `docs` 规则再次硬编码 `ln -fs` | 只修子目录规则不够，必须检查所有递归 Makefile |
| `43803` | `data` 规则直接执行 `driver-list-format.sh` | HMDFS 上脚本不能依赖直接 exec，需经 `SHELL` |
| `6990` | `make check` 后续阶段找不到 `gawk` | 绝对路径编译器可用不代表 HNP 工具目录在 PATH |
| `38515` | test_package 假定 daemon 位于 `sbin/upsd` | 测试必须以实际 Conan package tree 为准 |
| `21715` | 版本断言写死不存在的 `NUT` 大写文本 | 消费者断言应匹配真实命令契约，而不是猜测文案 |
| `44728` | 为修复审查而恢复 `umask 077` 后 `config.status` 写 `subs1.awk` 被拒 | 022 不能全局替换，但 OHOS 的 config.status scratch 需要按 `linux-ohos` 主机条件局部选择 |
| `44740` | 审查修复后的完整 Conan/消费者链 | `test_package`、L0 和 L1 通过 |
| `44802` | 当前 PR head 的复核构建 | 全部 workflow steps、`test_package`、L0 和 L1 通过；cleanup 仅有非阻断 CI 基础设施 warning |
| `48628` | 上述问题全部收敛 | `make check`、打包和 test_package 均通过 |

这些失败分别属于配置后生成物、上游测试规则、设备工具环境和消费者
契约四个边界。把它们都归因于“权限问题”或只增加 `chmod` 会漏掉后续
失败；把 `make` 成功写成上游测试通过也会形成假证据。

## 3. 推荐适配方法

### 3.1 配置后审计生成规则

在第一次 configure 后，检查 `Makefile.in` 和生成的 Makefile，而不是只读
`configure` 输出：

```sh
rg -n 'ln -f|driver-list-format\.sh|SHELL|LN_S|AWK' \
  . Makefile.in docs data tests
```

对 OHOS 专属路径，保留其他平台行为：

1. 把文档和测试中硬编码的 `ln -fs` 改为 `$(LN_S)`；
2. 把直接执行的校验脚本改为 `$(SHELL) script ...`；
3. 同时修改源码侧 `Makefile.in` 和实际生效的生成文件来源，避免下一次
   clean build 重新生成旧规则；
4. 不把全局 `LN_S=cp` 或删除测试作为默认修复。

### 3.2 为完整上游测试保留工具环境

配置阶段拿到绝对路径 `clang`，不等于 `make check` 能找到 `gawk`、`make`
或其它 HNP 工具。配方应在 OHOS 分支中为整个 configure/build/check 进程
显式前置 `/data/service/hnp/bin`，并对 Autotools 归档探测显式设置
`AR`/`RANLIB`。这样构建和测试使用同一环境，不需要修改共享 profile。

推荐检查：

```sh
test -x /data/service/hnp/bin/llvm-ar
test -x /data/service/hnp/bin/llvm-ranlib
command -v gawk
make -j1
make check -j1
```

`-j1` 是本适配的设备稳定性选择；它不能替代测试执行，也不能把失败
转换成成功。

### 3.3 用实际包布局设计消费者测试

消费者测试先枚举或检查 Conan package folder 的实际产物，再执行真实命令：

```sh
test -x "$(command -v upsc)"
test -x "$(command -v upsd)"
upsc -V
upsc -h
upsd --version
```

版本断言应来自真实输出契约，例如
`Network UPS Tools upsc 2.8.5`，不要假定命令一定输出项目简称
`NUT`。daemon 位于 `bin/` 还是 `sbin/` 也必须以 package() 的结果为准，
不能仅凭传统 FHS 习惯猜测。

## 4. 可复核证据

最终标准 runner：

`codex-2.8.5-nut-2.8.5-20260911-conan-20260911-233949-48628`

结果：

- exit code `0`，单包 `Success: 1`、`Failed: 0`；
- `make -j1` 和 `make check -j1` 完成；
- 上游测试 4 passed、0 failed、0 errors；
- 基线 run `48628` 已验证 `make check` 的 4 个默认上游测试和原消费者
  检查；审查修复后的 AtomGit CI `44740` 又验证了新增的 `upsd --version`
  断言，修订后的 `test_package` 8 项断言全部通过；当前 PR head 在 AtomGit
  `44802` 再次复核通过；
- L0/L1/L2/L5 通过，L4 的旧结果曾因平台宏形式的 `getpass` fallback 被扫描
  为 warning；本次审查修订改为 configure 特性探测，且将 `umask 022` 收窄到
  `linux-ohos` scratch 目录。AtomGit `44802` 的公开摘要未单独列出 L4；
- Conan package reference：
  `nut/2.8.5#d39703f7c344bc45beb2f39d0d43089a:6b129b068851896169fae42d399fa922d239ce8a#e3e486d055572a7f2263fdea09c8ab9e`。

复现入口：

```sh
CI_PACKAGES="archives/n/nut/2.8.5" \
  zsh ci/conan/build_and_test.sh
```

## 5. 复用边界与禁止做法

本条目可复用到同类旧式 Autotools 包，但不能把 NUT 的命令名、目录名或
测试数量直接复制到其它库。复用时必须重新核对：

- configure 选择的 `LN_S` 与每个递归 Makefile 是否一致；
- 每个 make/test hook 是由 shell 解释还是直接 exec；
- 当前 runner 的 HNP 工具目录和 PATH；
- package() 真实安装出的 bin/lib/include 路径；
- `--version`/`--help` 的实际输出契约。

禁止：

1. 只改生成后的 Makefile，不回写其 `Makefile.in` 或补丁源；
2. 只看到 `make` 通过就声称 `make check` 已通过；
3. 用 `chmod +x` 掩盖 HMDFS 的直接脚本执行限制；
4. 为满足断言而把 `sbin`、版本文案或测试结果写成想象中的布局；
5. 因 L2 某个非核心命令的非阻塞 warning，就删除真实测试或伪造全量通过。

## 6. 路径 B 评审说明

本草稿的候选贡献是“生成 Autotools 规则审计 + HNP 工具环境闭环 +
实际包布局消费者验证”的组合方法，且有多轮真机失败到成功的可追溯
证据。它不是单纯的 config.guess、umask、symlink 或 getpass 修复。
正式是否认定为 B 类难度库、是否计分，以知识库主编和赛事评审为准。
