# 内核模块类软件在 OHOS 的分层交付模式（用户态层 + 源码快照 + fail-closed 契约）

> 草稿来源：lenovolegionlinux 0.0.20 适配任务（PR [#11320](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/11320)）
> 状态：DRAFT（待评审转正式 E 条目）
> 日期：2026-09-20
> 配对草稿：`DRAFT-lenovolegionlinux-0.0.20-kernel-module-not-deliverable`（判定清单 / 禁止项）

## 1. 适用场景

三方库的交付物包含内核模块（Kbuild `obj-m`、`dkms.conf`、发行版 kernel driver），
**但同时**具备下列任一条件：

- 提供用户态组件（CLI / 库 / 脚本）可作为独立 conan 制品安装；
- 上游源码与测试脚本可与制品一并归档（例如上游 `tests/*.sh` 中存在不依赖内核态的子集）。

前者决定「能不能交付」，后者决定「能验证到什么程度」。二者都成立时，不应只写一份
「无法适配」说明关单。

## 2. 五步落地（每步都有机械可核验产物）

### ① 用户态层真实交付（`package_type=application`）

| 要点 | 做法 | 核验 |
|---|---|---|
| 真实编译步骤 | `build()` 用目标解释器对交付模块做 `compileall`（逐文件 `Compiling ...` 日志） | conan create 日志 |
| 制品布局 | `lib/pythonX.Y/site-packages/<pkg>/` + `bin/<cli>`（对齐上游 `console_scripts`） | `find <pkg>/lib -name site-packages` |
| 入口可用性 | 入口脚本内自带 site-packages 定位（`dirname(dirname(__file__))/lib/pythonX.Y/site-packages`），使 `bin/<cli> --help` 在 conanrun 之外也能跑通 | CI L2 冒烟 `--version/--help` |
| 工具声明 | 软件级 `commands.json`（R38，`type: "tool"`） | CI L0k |
| 消费者测试 | `test_package` 真实 import 并调用包内 API（R34），不得只断言文件存在 | CI L1a/L1b |

### ② 上游源码按原目录布局随包交付

`share/<pkg>/upstream/{<module_dir>,tests,python,...}`，价值有两个：

1. 上游**源树变体**的测试脚本可**逐字执行**——脚本用 `BASH_SOURCE` 定位自身，
   相对路径（`${DIR}/../python/.../cli.py`）在快照内天然成立，无需改一行；
2. 平台将来提供内核构建树 / 内核头制品时可直接复用快照，不必重新拉取上游。

### ③ 内核模块源码 fail-closed 契约测试

对包内源码做静态契约校验并保留「不得伪造」的机械保障：

```bash
require "module_init() present"  "module_init("        "$SRC"
require "Kbuild obj-m present"   "obj-m"               "$MAKEFILE"
require "DKMS declared"          "BUILT_MODULE_NAME"   "$DKMS"
KO="$(find "$SNAP" -name '*.ko' -print -quit)"; [ -z "$KO" ] || fail "prebuilt .ko shipped"
```

源码缺失/契约缺失一律非 0 退出（绝不静默通过）；**不声称**这是内核态功能验证。

### ④ 平台特有测试（鸿蒙特有测试）

在目标机（无 Legion 内核接口的 OHOS PC 基线）上必须验证的是**降级行为**而不是功能：

- 断言 stdout 文案（如 "kernel module is not loaded"）而**不是退出码**——实测上游
  `main()` 不传播子命令返回值，退出码恒为 0，用退出码断言会写成假测试；
- 断言无 Python traceback；
- 断言打包契约（site-packages 布局、`bin/` 入口可执行）与「不得交付预编译 `.ko`」。

### ⑤ 分层声明（PR 描述 + manifest.yaml + test_package/MANIFEST.yml）

三处都要写清「已执行并通过」与「未执行（附实测原因）」，未执行项**不进通过数**。
`MANIFEST.yml` 建议显式列出 `not_verified:` 段，避免把「源码契约通过」误读为「内核态通过」。

## 3. 依赖处置规则（本模式的高频坑）

上游 `install_requires` 中在制品仓**没有制品**的条目要分两类处理：

| 类别 | 判据 | 做法 |
|---|---|---|
| 功能必需 | 不装则交付物无法启动/无法工作 | 必须解决（补配方立项 / 换实现），**不得**跳过测试或删功能 |
| 可选辅助 | 只影响附加能力（shell 补全、主题检测等） | 按上游既有的可选依赖写法降级为 `try/except ImportError` + 调用点守卫，并在 PR 中说明理由；补丁不得含平台宏（R8） |

本例实测：`PyYAML` 制品仓有（`pyyaml/6.0.2`，作为 `requires`）；`argcomplete` 无制品但仅提供
shell 补全（`legion_cli` 的功能路径不依赖它），按其上游对 `darkdetect` 的同一写法降级为可选；
`PyQt6`/`darkdetect` 属 GUI 侧，GUI 交付物因此如实声明未执行。

## 4. 实测结果（lenovolegionlinux 0.0.20）

| 项目 | 结果 |
|---|---|
| `conan create`（ohos-aarch64） | exit 0；用户态层 `compileall` 全量编译通过 |
| 上游用例（12 个） | **执行 2 通过 2**（`tests/test_python_cli.sh` 逐字执行 + `tests/test_python_cli_installed.sh` 逐字副本跑包内 `bin/legion_cli`），其余 10 个逐条阻塞并附原始报错 |
| 适配侧新增用例 | 3 个（消费者 API 8 断言 + 鸿蒙平台 11 断言 + 内核模块源码契约 14 断言），33/33 通过 |
| 仓库 CI（`ci/conan/build_and_test.sh` 本地同构复现） | G0/KC/JC pass；L0 pass；L1 pass（含 L1e 破坏性反向验证：移走 `bin/`+`lib/` 后测试必失败）；L2 pass；L4 pass；L5 pass；pass rate 1/1 |

## 5. 禁止项

1. 伪造内核内部头 / 空壳 stub 让源码「编译通过」；
2. 交付预编译 `.ko`（应由 fail-closed 断言拦截）；
3. 只交付用户态层却不声明内核态边界（「裁剪后宣称完成」）；
4. 把「源码契约通过」写成「内核态功能通过」；
5. 用 `manifest.yaml: status: published` 覆盖未构建的内核态部分。
