# conan-verify 补测报告 — daemontools-encore 1.11

`reports/conan-verify-report.md` 中 G4 打印 `⚠️ 无法找到程序包 ID`，L2/L4/L5 打印 `✅ PASS` 与 `⏭️ 跳过（无 cache 路径）` 并存。按工作区口径（第 7.2 节）以跳过行为准，即这四项没有自动证据，本文件按固定两条口径补齐。

原因与包形态有关（`package_type = "application"`）：包内既无 `lib/` 也无 `include/`，G3 自身也打印 `ℹ️ 无 lib/ 目录（纯可执行包）`，工具的程序包定位路径解析失败后 L2/L4/L5 一起走「无 cache 路径」分支。

- 提交：`cf7bea0d9051b8993dd847543af726fab04212e0`
- 采信轮包目录：`/storage/Users/currentUser/.conan2/p/b/daemo5cdac5efc9ae4/p`（`conan-verify` 轮，G2 已真清缓存）
- 原始证据：`reports/conan-verify-supplement-raw.log.md`（L4 表 + L5 两轮哈希）、`reports/conan-verify-supplement-L2.log.md`（L2 直接运行）、`reports/l5-payload-round{1,2}.sha256`

## G4 产物完整性

`package_info()` 声明与实际内容一致（`bindirs = ["bin"]`，`libdirs`/`includedirs` 为空）：

```
$ find <package> -type f | wc -l
42
$ find <package> -type f | sed 's|<package>/||' | sort
bin/envdir            bin/envini          bin/envuidgid      bin/fghack
bin/multilog          bin/pgrphack        bin/readproctitle  bin/setlock
bin/setuidgid         bin/setuser         bin/softlimit      bin/supervise
bin/svc               bin/svok            bin/svscan         bin/svscanboot
bin/svstat            bin/svup            bin/tai64n         bin/tai64nlocal
licenses/LICENSE
share/man/man8/{envdir,envini,envuidgid,fghack,multilog,pgrphack,readproctitle,setlock,setuidgid,softlimit,supervise,svc,svok,svscan,svscanboot,svstat,svup,tai64n,tai64nlocal}.8
conaninfo.txt  conanmanifest.txt   (conan 元数据)
```

- `bin/`：20 个文件，与上游 `BIN` 清单逐条一致，全部带可执行位（`for f in bin/*; do [ -x "$f" ] || echo NOT_EXEC; done` 无输出）。
- `share/man/man8/`：19 个手册页。上游 `MAN` 清单共 20 条文件条目（补丁后其中 `setuser.8` 一条带 `?` 可选前缀），实际安装 19 条；该文件 1.11 发行版未提供，见 `reports/upstream-install-scenarios.log.md` 场景 B/C（补丁前 `installer` 在此处 111 退出）。
- `licenses/LICENSE`：由 `package()` 复制。
- 无多余文件（无构建中间产物、无 `.o`/`.a`、无 autotools 中间脚本）。

## L2 平台功能矩阵（真实执行）

完整原始输出见 `reports/conan-verify-supplement-L2.log.md`，摘要（全部在设备上直接执行包内产物）：

| 命令 | 实测结果 |
|------|----------|
| `bin/envdir <dir> /bin/sh -c 'echo $Message'` | 输出 `This is a test. This is only a test.`，rc=0 |
| `printf 'one\ntwo\n' \| bin/multilog t <logdir>` | rc=0，`logdir/current` 内容 `@400000006aa3703819f86e0c one` / `@400000006aa3703819f871f4 two`（带 TAI64N 时间戳） |
| `printf 'ONE\n' \| bin/tai64n \| bin/tai64nlocal` | `2026-09-11 11:06:22.478744500 ONE`，rc=0 |
| `bin/softlimit -c 0 python3 -c 'import resource;print(resource.getrlimit(resource.RLIMIT_CORE)[0])'` | `0`，rc=0（子进程 core 上限确被下调） |
| `bin/setlock <lock> /bin/sh -c 'echo lock-held'` | `lock-held`，rc=0 |
| `bin/svok <已存在但未监管的目录>` | rc=100（上游 `rts.tests/nonexistent.exp` 语义） |
| `bin/svok <不存在的目录>` | `unable to chdir to ...: file does not exist`，rc=111 |
| `bin/svstat <已存在但未监管的目录>` | `unable to open supervise/ok: file does not exist`，rc=0 |
| `bin/svc <已存在但未监管的目录>` | `warning: unable to control ...: file does not exist`，rc=0 |
| `bin/supervise <不存在的目录>` | `fatal: unable to chdir to ...`，rc=111 |
| `bin/supervise <含 run 的服务目录>` | `fatal: unable to read supervise/control: file does not exist`，rc=111（**快速退出，不挂死**） |

补充：`bin/svscanboot` 按上游设计是 `/bin/sh` 脚本（Makefile 规则 `cat warn-auto.sh svscanboot.sh > svscanboot`），不是 ELF，`file` 输出 `/bin/sh script`。

## L4 静态安全属性

对 `bin/` 下全部 20 个条目逐个 `readelf -h/-lW/-dW`（原始表见 `reports/conan-verify-supplement-raw.log.md`）：

- 19 个 ELF 全部为 `Type: DYN`（PIE）+ `GNU_RELRO` + `FLAGS: BIND_NOW` + `FLAGS_1: PIE` + `GNU_STACK RW`（NX 生效）；
- `DT_NEEDED` 只有 `libc.so`，无其它动态依赖；
- `bin/svscanboot` 是上游生成的 `/bin/sh` 脚本（非 ELF，无这些属性可言，按上游形态交付）。

## L5 产物基线与可复现性

同提交两轮真清缓存构建（轮 1 = 采信轮 `conan-verify`；轮 2 = 清缓存后独立 `conan create`）：

| 项目 | 结果 |
|------|------|
| 逐文件 sha256（`bin/` + `share/man/` + `licenses/`，40 个文件） | 两轮 `diff` 无差异（逐字节一致） |
| 内容聚合（包目录内相对路径，排除 `conaninfo.txt`/`conanmanifest.txt`） | 轮 1 `d43189014913589b79b96c352c6cb3e43223426b864ad10b68e3d5f1057326ad`；轮 2 同值 |
| 全包 `diff -r`（排除上述两个元数据文件） | 无差异 |
| `conanmanifest.txt` 首行（打包时间戳） | 轮 1 `1789094704` / 轮 2 `1789095954`（预期漂移，已排除） |

- 聚合命令在包目录内用相对路径：`find bin share licenses -type f | sort | xargs sha256sum | sha256sum`（避免分片目录名进入哈希）。
- 构建未使用 `-g`，也没有上游 `__DATE__`/`__TIME__` 内嵌，因此两轮无「跨目录调试信息偏移」类差异；结论是构建可复现。
- 逐文件哈希清单已随证据提交：`reports/l5-payload-round1.sha256`、`reports/l5-payload-round2.sha256`。

## W3 本地 CI 模拟侧的两处已知误报

`reports/w3-local-ci.log.md` 的结论是 `L0/L1/L2/L4/L5 = pass`、`Pass rate 100.0% (1/1)`，其中两项文案需要按实际语义判读：

- `L2: <工具> --version/--help failed (non-blocking)`（20 个里 15 个）：本包的 CLI 是 DJB 风格，**没有** `--version`/`--help` 长选项（`readproctitle` 等在无参数时以退出码 100 打印 usage，`supervise` 等把 `--version` 当服务目录名），因此这是工作区第 17 节列明的探针形态限制（只试 GNU 长选项且要求 rc=0），不是功能缺陷。本文件上面的 L2 表格用真实参数逐个执行，才是本包的 L2 证据。
- `L1c: No upstream make check/ctest in log`：符合预期——上游回归套件在本平台不能放进 `build()`（9 个用例会永久挂起 `make rts`），其执行证据在 `reports/upstream-test.log.md` 与 `reports/upstream-tests.md`。
- 该轮 `L1e` 破坏性负测试通过（把 `bin/` 移走后测试确实失败），可佐证 `test_package` 真正依赖被测产物而不是空跑。

## 与工具报告的差异说明

- `reports/conan-verify-report.md` 的 G0 命中 E490（autotools helper 脚本可执行位）与本包无关：本包是 DJB 风格手写 Makefile，没有 `configure`/`config.guess` 等 helper 脚本，G2 干净轮实测通过；按第 7.2 节「知识建议与实际错误类别无关时直接忽略」处理。
- 该报告在 `finish` 内嵌复审轮次会打印 `G0: configure 失败 (exit 127)`（工具内嵌 G0 预检硬编码 `./configure`），属工作区第 7.2 节列明的白名单项：本包无 `configure`，判读以清缓存 G2 为准。
