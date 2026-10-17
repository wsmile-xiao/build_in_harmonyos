# DRAFT-xdp-tools-1.6.3-optional-tool-gated-subset-build

**一类问题**：上游 `configure` 对**可选工具**和**依赖**的探测是**分支/环境条件性**的——
①可选工具缺失时探测失败即清空变量，顶层 Makefile 随之**静默不构建**依赖它的目标（产物变成子集）；
②有些依赖探针只在某一个分支里执行，另一分支直接 `return`，于是 `configure` **根本不会发现该依赖**。
配方若把 `configure` 当成"已替我探测好一切"，就会在链接期（缺 `-lpcap`）或打包期（少了一批可执行文件）翻车。
这不是某个库的补丁问题，而是一类"**对探测结果负责、而不是对探测动作负责**"的配方纪律。

## 使用说明（判定树 + 修法）

1. **判定"可选工具 → 子集构建"**：
   configure 输出出现 `bpftool not found or doesn't support skeleton generation; not building all tools`，
   且顶层 `Makefile` 里是 `ifneq ($(BPFTOOL),)` 之类的包含逻辑；构建后 `ls sbin/` 少于文档宣称的工具数。
   → 这是上游**既定行为**：不要伪造全量，如实声明实际产物；
   若业务必须全量，则把缺失工具作为 `tool_requires`/预置二进制补进构建环境。
2. **判定"依赖探针藏在分支里"**：
   `grep -n 'check_pcap\|USER_LIBS' configure */Makefile`，若探针只在 vendored 分支、而配方走 system 分支
   （如 `FORCE_SYSTEM_LIBBPF=1`），则 `configure` 不会把该依赖的 flags 写进 `config.mk`；
   构建到该模块时才会报 `fatal error: 'pcap/pcap.h' file not found` / `cannot find -lpcap`。
   → 修法：配方从依赖包解析 `cpp_info`（includedirs/libdirs）并**显式注入** `CFLAGS`/`LDFLAGS`，
   不依赖 `configure` 的分支探针。
3. **收尾**：构建后**枚举**真实产物（`find <pkg> -maxdepth 2 -type f -perm -u+x`），据此写
   `commands.json` 与 `package_info.bindirs`；把"缺可选工具 → 目标被跳过"写进 notes/MANIFEST。

## 适用范围

- 用自定义 `configure`/`Makefile`、且"可选工具决定构建子集、依赖探针在分支里"的项目；
- crossover/OHOS 环境：**宿主**探测到的工具/依赖与**目标**环境不一致，最容易踩；
- 任何把"未探测到"默认当"不需要"的构建系统。
- **不适用**：CMake/autotools 且 toolchain 已统一注入全部依赖 flags 的项目。

## 输入输出定义

| | |
|---|---|
| 输入 | `configure` 的探测输出；`Makefile`/子 Makefile 里可选工具的门控与 `USER_LIBS`；Conan 依赖包的 `cpp_info` |
| 输出 | 显式注入的 `-I`/`-L`/`-l`（对未探测依赖）；与实际 `sbin/` 一致的 `commands.json`/`bindirs`；文档化的子集说明 |
| 成功判据 | `conan create` 退出码 0；`ls sbin/` 与 `commands.json` 一致；无"缺头/缺库"链接错误 |

## 示例（xdp-tools 1.6.3，真实）

- **可选工具门控**（`logs/025f-conan-create-cross.log`）：
  ```
  bpftool not found or doesn't support skeleton generation; not building all tools
  UTILS := xdp-filter xdp-loader xdp-dump          # 顶层 Makefile:19
  ifneq ($(BPFTOOL),) UTILS += xdp-bench xdp-forward xdp-monitor xdp-trafficgen   # :21-23
  ```
  → 最终只出 **3/7** 工具（`sbin/xdp-loader`、`sbin/xdp-filter`、`sbin/xdpdump`）；`commands.json` 按 3 个声明。
- **依赖探针分支**（`configure:322-407`）：
  `check_libbpf()` 在 system-libbpf 分支 `return 0`（`:357`），**zlib/elf/pcap 探针只在 vendored 分支末尾**
  （`:398-405`）执行；而 `xdp-dump/Makefile:12` 无条件 `USER_LIBS = -lpcap`。
  → 配方在 system-libbpf 下显式注入 libpcap 的 `-I/-L`（见 `conanfile.py::_pcap_flags`）。

## 查重差异表（与最相近条目逐条比）

| 维度 | E334（fastnetmon 抓包后端门控） | 本条 |
|---|---|---|
| 取向 | **主动关闭** Linux-only 后端（`ENABLE_AF_XDP_SUPPORT=OFF`） | **按上游探测**被动形成子集 + 对未探测依赖负责 |
| 触发 | 配方显式设 CMake 选项 | 上游 `configure` 的可选工具门控 / 分支探针 |
| 风险点 | 依赖闭包膨胀 | 链接期缺依赖 flags；打包期产物与声明不一致 |
| 解法 | feature gate + 文档 | 显式注入 cpp_info flags + 枚举真实产物 + 如实申报 |

`bpftool` 在 `knowledge/{graph,drafts,doc}` 词边界 **0 命中**（仅 operations 文档提及）；`libpcap` 命中的是
E334 与 irpas 草稿（musl 符号/捆绑替换），均不覆盖"子集构建 + 条件探针注入"。

## 验证证据

```
$ python3 scripts/ohc-run.py init-build xdp-tools 1.6.3 --url=<official>
$ conan create archives/x/xdp-tools/1.6.3 -pr:h=ohos-aarch64-wsl -pr:b=default -r=ohpcd --build=missing
  bpftool not found ... not building all tools
  libbpf support: system v1.5.1 ; ... ; secure_getenv support: no ; cap-ng support: no
  CLANG xdpfilt_*.o ; CC xdp-filter ; CC xdp-loader ; CC xdpdump      # 三个工具
  Package '...' created                                               # EXIT=0
$ conan-verify ... --profile ohos-aarch64-wsl
  Verdict: PASS (G0/G1/G2/G3/G4)
$ python3 scripts/ohc-run.py finish xdp-tools 1.6.3 built
  ✅ 本地 CI 模拟通过 (reports/w3-local-ci.log)
```

日志：`/mnt/e/dsh working/tasks/xdp-tools-1.6.3-2026-09-25/logs/025f-conan-create-cross.log`、
`archives/x/xdp-tools/1.6.3/reports/conan-verify-report.md`、`reports/w3-local-ci.log`。
来源事件：xdp-tools 1.6.3 OHOS 适配（任务 #12086，分支 `feat/xdp-tools-1.6.3`），2026-09-25。
