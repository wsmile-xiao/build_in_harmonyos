# HMDFS 大小写不敏感致 make 中间产物规则被静默跳过

> 草稿条目（DRAFT）— 配套 `mbr-1.2.2-hmdfs-case-insensitive-make-intermediate-rule-skip.kv`
> 样例库：`archives/m/mbr/1.2.2/`（知识库拓展四件套随该 PR 提交）

## 现象

make / Autotools 项目在鸿蒙 HMDFS 上构建，出现与真实原因隔了两层的报错：

- mbr 1.2.2 实测：`configure` rc=0，`make -j1` **rc=2**，`as86` 报
  `unbound label ... not defined` **87 条**；
- 中间产物（`.i86`/`.b`）从未生成，但**源文件未被改动**
  （`mbr.S86` 10562 B，`cmp -s` 与上游 tarball 逐字节一致）；
- 在大小写敏感文件系统（ext4/xfs、CI 容器）上同一份源码**不报错** —— 问题只在鸿蒙本机暴露。

## 根因

HMDFS 大小写不敏感（同 vfat/exfat/默认 APFS、Windows）：`mbr.s86` 与 `mbr.S86` 是同一路径。

```
SUFFIXES = .b .S86 .s86
%.s86: %.S86            # 预处理：$(CC) -E -xc $< -o $@   ← 被跳过
%.b:   %.s86            # 汇编：  as86 -0 -b $@ $<
y2k.s86: mbr.S86        # 显示规则：同样被跳过
```

make 判定「中间产物 `mbr.s86` 已存在」（其实它就是源文件 `mbr.S86`）→ **跳过预处理配方** →
`as86` 直接读取含 `.if`/宏定义、尚未经 C 预处理的 `mbr.S86` → 整片标签未定义。

**关键判别点**：源文件哈希与上游一致 ⇒ 不是「产物覆写源」，而是「规则被跳过」。

## 识别

1. 文件系统探针：写入 `CaseProbeTest.txt`，以 `caseprobetest.txt` 读回，可读 ⇒ 不敏感文件系统；
2. 规则撞名扫描：`Makefile.am` / `Makefile.in` / `Makefile` / `*.mk` 中「目标: 前置」或
   `SUFFIXES` 项仅大小写不同 ⇒ 命中。

已固化为 `archives/m/mbr/1.2.2/knowledge-extension/detect-case-insensitive-build.sh`
（命中 rc=1，可直接串门禁；临时目录 `${TMPDIR:-/tmp}`，无本地绝对路径依赖）。

## 修复（策略 S1，mbr 采用）

中间产物后缀改成与源文件不撞名：`.s86` → `.i86`，双写 `Makefile.am`（9 处）+ `Makefile.in`（10 处），
覆盖 `SUFFIXES` / `CLEANFILES` / `%.i86: %.S86` / `%.b: %.i86` / `%.o86: %.i86` / 显式规则
`y2k.i86`、`testdisk.i86`。不引入任何平台宏（PF5 拦截），在大小写敏感系统上同样成立。

备选：S2 源外构建 + 显式等价规则；S3 无法修复时 `env_unsupported` 标记。详见
`knowledge-extension/strategy.md`。

## 验证

| 阶段 | 命令 | 结果 |
|---|---|---|
| 未启用 | `configure` → `make -j1` | rc=2，`unbound label` 87 条，无中间产物，源文件未改动 |
| 启用（S1） | `patch -p1` → `make -j1` | rc=0，`install-mbr` 39296 B、`mbr.b`/`testdisk.b` 512 B、`y2k.o` 1480 B |
| CI 口径 | `ci/conan/setup.sh` + `build_and_test.sh` | 通过（G2 干净 `conan create` + L2/L4/L5），`test_package` 14/14 |

端到端复现脚本：`knowledge-extension/reproduce.sh`（阶段 A 复现报错 / 阶段 B 验证生效，
日志重定向到文件，规避 SIGPIPE）。

## 边界与限制

- 大小写敏感文件系统不触发，因此**检测必须在鸿蒙本机执行**，远端 CI 不能替代；
- 上游有意依赖大小写区分同名文件（`Makefile` 与 `makefile` 并存）时须人工确认后改用 S2/S3；
- 对照实验（大小写敏感 FS 上跑未打补丁版本做字节比对）在本机未能完成：
  `/dev/shm` 挂载目录 `mkdir` 被拒（`Permission denied`），结论基于规则语义与产物一致性判定。

## 关联

- 同族共性问题：HMDFS 大小写不敏感（configure 派发 / `.pc` 别名解析路径）；
  本条为同族**新机制**——make 中间产物规则被跳过。
- 样例库 PR：mbr 1.2.2（`archives/m/mbr/1.2.2/`）。
