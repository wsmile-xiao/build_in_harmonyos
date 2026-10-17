# Imake/xmkmf 遗产 X11 库在 OHOS 上的适配（知识库拓展）

> 样例库：`archives/x/xli/1.17.0-20061110`（xli 1.17.0，2006-11-10 发行快照）
> 同 PR 交付；检测脚本 + 复现脚本 + 两条知识条目位于本目录与 `knowledge/drafts/`

## 1. 一句话

OHOS SDK 的 native 工具链（clang/llvm）**不含 imake/xmkmf**，而 1990s–2000s 的
一批 X11 客户端/工具以 `Imakefile` 为唯一构建描述——工具缺失时源码树里根本没有
`Makefile`。共性解法是：**优先走发行快照自带的非 Imake 构建路径
（`Makefile.std` / `Makefile.noimake` / `Buildfile`），把 Imake 的 `-I/-L/-l`
解析替换为 Conan 依赖注入**，并对同批老代码常见的 musl libc 缺口做逐函数最小定向修复。

## 2. 触发场景（何时该读本拓展）

| # | 现场现象 | 判定 |
|---|---------|------|
| 1 | `imake: command not found` / `xmkmf: command not found` | 命中 |
| 2 | `make: *** No targets specified and no makefile found`，而源码树里有 `Imakefile` | 命中 |
| 3 | 上游站点已下线（HTTP 404）、只剩发行快照 tarball（2000 年代时间戳） | 命中（叠加因素） |
| 4 | 源码树有 `configure` / `CMakeLists.txt` / `meson.build` | 不命中，走常规适配路径 |

## 3. 识别：规则 + 检测脚本

规则（脚本 `detect_imake_legacy.py` 的两级识别）：

- **A 类（构建系统）**：源码树存在 `Imakefile`（任意层级）／`README*`、`INSTALL*`、
  `*.spec`、`Makefile*`、`*.sh` 中提及 `imake|xmkmf`；并列出是否自带
  **回退构建文件**（`Makefile.std` / `Makefile.noimake` / `Buildfile` / `Makefile.orig`）
  与现代构建文件（`configure` / `CMakeLists.txt` / `meson.build`）。
- **B 类（libc 缺口）**：源码（`.c/.h/.cc/.cpp`）调用 BSD 遗留函数
  `rindex|index|bcopy|bzero|bcmp`；并对目标 libc 做符号探针
  （`nm -D --defined-only`，`--libc` 指定或读 `OHOS_SDK_SYSROOT`）。

```sh
# 用法（只读，无绝对路径硬编码）
python3 detect_imake_legacy.py --src <源码目录> [--libc <libc.so>] [--json]
# 退出码：0=未命中  1=命中（按下方策略处理）  2=参数/环境错误
```

**实测证据（2026-10-04，OHOS worker / SDK 26.0.0.18）**：

| 探针 | 结果 |
|------|------|
| `command -v imake` / `command -v xmkmf` | 均为空（**MISSING**） |
| `libc.so` = `.../ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/lib/aarch64-linux-ohos/libc.so` | — |
| `nm -D --defined-only libc.so` → `rindex` | **0（缺失）** |
| 同探针 → `index` / `bcopy` / `bzero` / `bcmp` | 各 1（存在） |
| 上游 xli 1.17.0 源码树测试清点 | **无 test/check 文件**（上游无测试套件） |

## 4. 处理策略

| 策略 | 前提 | 做法 |
|------|------|------|
| **S1（首选）** | 源码自带 `Makefile.std`/`Makefile.noimake`/`Buildfile` | 以其为构建入口直编；`INCLUDES/LIBS` 换成 Conan 依赖注入（展开 `self.dependencies[*].cpp_info`，见样例 `conanfile.py::_dependency_flags()`） |
| **S2（次选）** | 无回退构建文件 | 按 `Imakefile` 语义手工重建最小 `Makefile.ohos`（`INCLUDES→CPPFLAGS`、`LIBS→LDLIBS`、`SRCS` 与 `NormalProgramTarget` 等目标照抄），作为补丁随配方携带 |
| **S3（禁止）** | — | 不引入 `imake/xmkmf` 的 `tool_requires`（环境内不存在，只把失败点后移）；不把"装个 imake 就好"当作结论 |

**配套 libc 修复（最小定向）**：本环境仅缺 `rindex` → 注入编译期等价替换
`-Drindex=strrchr`（`rindex(s,c) ≡ strrchr(s,c)`）。
**禁止** 启用上游 `-DSYSV` / `-DSVR4` 总开关：会连带打开 `stropts.h` / `F_FREESP` /
`poll` 等更大缺口（样例如是修，缺口数从 1 变一片）。同族函数逐函数处置，先探针确认。

## 5. 适用库范围

- **适用**：1990s–2000s 的 X11 系包（X11 客户端/工具/字体工具等），源码树含
  `Imakefile` 且无现代构建系统；发行 tarball 自带回退构建文件者为最佳对象。
- **不适用**：现代 CMake/Meson/Autotools 工程（无需本策略）；无源码或已在 main
  合入的库；纯数据/脚本包。
- **典型同族候选**：xli（样例）、xmcd、xpaint 等 Imake 时代 X11 客户端。

## 6. 限制与边界

1. S1 仅在源码树**自带回退构建文件**时成立；否则需 S2 手工重建（成本高、逐包成立）。
2. `Makefile.std` 直编需在配方内手工展开依赖的 `-I/-L/-l`——Imake 的 include/lib
   自动解析在无 imake 时不可用（Conan 的 autotools/cmake 生成器不适用）。
3. `-Drindex=strrchr` 是编译期等价替换；若个别代码依赖 `rindex` 的非标准返回语义
   （实践中未见），需人工确认后改走补丁 shim。
4. 验证能力边界：CI 无显示环境，样例库的免显示 CLI（`xlito`）可全链路验证；
   图形路径只能用 `xli -help` / 启动即退的方式覆盖，真机显示需外部环境。

## 7. 复现

```sh
# 识别 + 探针（输出只进日志文件，不接管道，规避 SIGPIPE）
sh reproduce.sh --src <源码目录> [--libc <libc.so>] --log ./imake-legacy-repro.log
# 需要连样例库一起跑（干净环境 conan create）：
CONAN_REPRO=1 sh reproduce.sh --src <源码目录> --repo <仓库根>
```

样例库完整复现（仓库根执行，日志落文件）：

```sh
conan create archives/x/xli/1.17.0-20061110 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    > conan-create-xli.log 2>&1
```

实测结果：`conan create` 全绿（G0–G4 + L2/L4/L5 门禁通过，含 `test_package/`
消费者用例：`xlito` 往返转换 + `xli` 启动），安装前缀内 `bin/xli`、`bin/xlito` 就位。

## 8. 交付物清单（本拓展）

| 件 | 位置 |
|----|------|
| 问题识别规则/检测脚本 | `knowledge/drafts/imake-legacy-x11/detect_imake_legacy.py` |
| 处理策略 + 完整文档 | 本 README（第 3–4 节） |
| 复现脚本 | `knowledge/drafts/imake-legacy-x11/reproduce.sh` |
| 样例演示库 | `archives/x/xli/1.17.0-20061110/`（配方 + 消费者测试） |
| 知识条目①构建系统 | `knowledge/drafts/DRAFT-xli-1.17.0-imake-absent-makefile-std-fallback.{kv,md}` |
| 知识条目②libc 缺口 | `knowledge/drafts/DRAFT-xli-1.17.0-ohos-musl-missing-rindex-bsd-legacy.{kv,md}` |

## 9. 相关

- 同族思路：`knowledge/drafts/werror-autotools/`（另一类"上游构建脚本不适配 clang"
  的拓展，检测脚本 + README + 样例库同构）。
- 覆盖判断：本条目不解决 `-Werror` 升级问题（见上）；也不替代 musl syscall 缺口
  （`setreuid` 等，见 P008/E051）。
