# jgraph 83 适配测试报告

- 软件 / 版本: jgraph 83（上游 Jim Plank's jgraph，README `$Revision: 8.3 $`）
- 适配平台: HarmonyOS PC / aarch64（OHOS SDK clang 15.0.4；Conan 2.29.1）
- 源码: `https://deb.debian.org/debian/pool/main/j/jgraph/jgraph_83.orig.tar.gz`
  sha256 `e413b98a3ace184c4213d0bf025a2f433bb3f4be52d92ff64e8fa30016920546`
- 日期: 2026-09-21

## 一、上游测试情况（N=0）

上游 83 源码包不含任何测试套件。以下证据均在未修改的 `.orig` 树上实测：

| 检查 | 命令 | 结果 |
|------|------|------|
| 测试目录 | `ls -d tests test` | 不存在（源码仅 16 个 `.c`/`.h`，其余为示例 `.jgr`/man/README 等） |
| check 目标 | `make -n check` | `make: *** No rule to make target 'check'.  Stop.` |
| test 目标 | `make -n test` | `make: *** No rule to make target 'test'.  Stop.` |
| makefile 目标清单 | `grep -nE '^[a-zA-Z0-9_.-]+:' makefile` | 仅 `all`/`examples`/`jgraph`/`sin`/`clean` 与文件依赖规则，无 `check`/`test`/`install` |

makefile 的 `examples` 目标只是用刚构建的二进制把示例 `.jgr` 渲染成 `.jps`，
没有任何断言或结果比对，因此不计为测试用例。

**结论：上游用例数 N=0；本适配按 R51 补充消费者测试（见下）。**

## 二、适配后测试

### 2.1 消费者测试（`test_package/test_jgraph.sh`，25 断言）

在 `conan create` 的 test 阶段由 `conan test` 自动执行（CI L1/L1e 覆盖）。
脚本驱动安装后的 `jgraph` 二进制，全部为真实执行 + 输出断言（非空壳）：

| 用例 | 断言 |
|------|------|
| 二进制安装可执行 | `command -v jgraph` + 可执行位 |
| 最小图形渲染（`-P`） | 退出码 0；`%!PS-Adobe-2.0 EPSF-1.2`；`%%BoundingBox: -27 -45 219 219`；`/Times-Roman findfont` |
| 渲染确定性 | 两次渲染 sha256 相同（输出无时间戳/随机量） |
| `-p` show 模式 | 退出码 0；含 `graph 0` / `xaxis` / 标题文本 / `curve 0` |
| `-L` landscape 平移（补丁 0001 修复项） | 退出码 0；landscape BoundingBox 字段顺序；平移值精确等于 `-bb[2]-bb[0]`（实测 -192.000000） |
| EPS 标记正常路径 | 退出码 0；输出非空 |
| 截断的 EPS `%%BoundingBox`（补丁 0001 负向对照） | 退出码 1；stderr 含 `eof in bounding box` |
| 多页输出（`newpage`） | 退出码 0；`%%Page: 1 1` 与 `%%Page: 2 2` |
| `-comments` | `^% ` 注释行 ≥ 10（实测 19） |
| 非法输入 | 退出码 1；`Bad token: bogus_keyword` |
| 产物架构 | AArch64 ELF（`e_machine=183`） |

运行结果（conan-verify G2 内实测）：

```
[step] jgraph consumer tests: 25 passed, 0 failed
```

### 2.2 上游示例回归（`.orig` 原始输入，逐字节未改）

```
for f in *.jgr; do jgraph -P < "$f" > /dev/null; done
```

- 20/21 个自带示例渲染成功；
- 唯一失败 `ad.jgr` 依赖 `cube.eps` 与 `disk.eps`（makefile 规则
  `ad.jps: cube.eps disk.eps`），两者生成后 `ad.jgr` 亦成功（23574 字节输出）
  —— 示例间依赖，非代码缺陷。
- 13 个 `complex-examples` 中 9 个独立渲染成功；`alg.jgr` 需从
  `complex-examples` 目录运行（`include "seq.jgr"`），`disk.jgr`/`regs.jgr`/
  `srm.jgr` 以 `newcurve` 开头但缺少顶层 `newgraph`，与 83 版解析器预期一致
  （非本适配引入）。

## 三、验证结果

| 项目 | 结果 | 证据 |
|------|------|------|
| 语言预检 (R47) | PASS，detected=c（cpp 兼容族） | `lang-preflight` 输出 |
| conan-verify G0-G4 | PASS | `reports/conan-verify-report.md` |
| conan-verify L2/L4/L5 | PASS（无 cache 路径时跳过，非阻塞） | 同上 |
| 本地 CI（L0/L1/L1e/L2/L4/L5） | PASS（Success 1/1，100%） | `reports/w3-local-ci.log` |
| W3 本地 CI（finish 内嵌） | PASS，exit_code=0 | `.ci-result.json`（log_sha256 `db6f5e9b…c1fa`） |

本地 CI 各门禁明细（`ci/conan/build_and_test.sh`，与平台 CI 同脚本）：

| 门禁 | 结果 | 说明 |
|------|------|------|
| L0（含 L0j/L0k/L0m） | PASS | commands.json 有效（type=tool）、目录结构合法、首次发布 |
| L1 / L1a / L1b | PASS | `conan create` 进入 test 阶段并执行 `test_package` |
| L1e（破坏性反向验证） | PASS | 移走 `bin/` 后测试失败 → 测试真实依赖被测包 |
| L2（smoke） | warn（非阻塞） | jgraph 无 `--version`/`--help`（非选项参数被当作输入文件名） |
| L4（补丁安全扫描） | warn（非阻塞） | `0010-token.c.patch` 命中 `strcpy` —— 均为上游 token.c 的上下文行，非本适配新增代码 |
| L5（产物基线） | PASS | `bin/` 有内容 |
| JC（垃圾拦截） | PASS | 增量模式（提交后按 diff 检查），无状态文件/二进制混入 |

功能证据（设备实测）：

```
$ jgraph -p < simple.jgr | grep '^bbox'
bbox -27 -45 219 219
$ jgraph -L < simple.jgr | grep -m1 ' 0 translate'
-192.000000 0 translate
$ jgraph -P < eps-bad.jgr; echo rc=$?
Error: Eps file 'eps-bad.eps': eof in bounding box
rc=1
```

## 四、结论

- 上游 N=0（有清点证据），本适配补充 25 条消费者断言，全部通过；
- 10 个补丁均为可移植性修复（无平台宏、无行为特性引入），其中 2 处是上游
  2007 快照与 Debian 83-26 均确认的真实缺陷（EPS 边界框 EOF 检测、
  landscape `%f` 传 `int`）；
- 包内容：`bin/jgraph` + `share/man/man1/jgraph.1`。
