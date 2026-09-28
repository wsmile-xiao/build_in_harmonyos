# simh 3.8.1 适配笔记

## 软件简介

SIMH 是多系统历史计算机模拟器。本包基于上游 V3.8-1（Robert M Supnik，
2009-02-08；`sim_rev.h` 中 `SIM_MAJOR=3 / SIM_MINOR=8 / SIM_PATCH=1`），
打包版本号沿用发行版命名 3.8.1。

- 官网：http://simh.trailing-edge.com/
- 语言：纯 C（C99）
- 许可证：MIT 风格（含「不得用作者名做宣传」条款，正文写在每个源文件头，
  归档不含独立 LICENSE 文件；`package()` 将条款正文写入 `licenses/LICENSE`）
- 产物：26 个独立命令行模拟器可执行文件

## 构建系统分析（W1）

- **类型**：纯 C + 手写 GNU makefile，无 configure/autotools/cmake。
- **无 install 目标、无 check/test 目标**，源码树不含任何测试文件。
- makefile 关键点：
  - `CC = gcc -std=c99 -U__STRICT_ANSI__ -g $(OS_CCDEFS) -I .`（CC 承载完整编译命令）
  - Linux 分支 `OS_CCDEFS = -lrt -lm -D_GNU_SOURCE`
  - `BIN = BIN/`；链接规则 `${CC} <srcs> <OPT> -o $@ ${LDFLAGS}`（LDFLAGS 位于源文件之后）
  - `all` 目标 = makefile 中 `ALL` 变量
  - `USE_NETWORK`（可选，需 libpcap）默认不启用

### 模拟器数量修正

makefile 的 `ALL` 列表**重复写了 `i1620` 一次**，且包含 `hp2100`、`s3`、
`altairz80`、`ibm1130`。去重后实际为 **26 个**：

```
altair altairz80 eclipse gri h316 hp2100 i1401 i1620 i7094 ibm1130 id16 id32
lgp nova pdp1 pdp10 pdp11 pdp15 pdp4 pdp7 pdp8 pdp9 s3 sds vax vax780
```

（本机以脚本复现 makefile 规则实测得 `ALL entries: 27, unique targets: 26`。）

## 依赖

- 运行时/构建依赖：仅 C 标准库（musl）+ libm，无第三方 Conan 依赖。
- 可选依赖：libpcap（仅 `USE_NETWORK` 时，本适配不启用 → `NETWORK_OPT` 为空）。

## 适配点

1. **CC 硬编码 gcc**：命令行覆盖
   `CC="clang -std=c99 -U__STRICT_ANSI__ -O2 -D_GNU_SOURCE -fcommon -I."`。
2. **-lrt 移除**：musl 无独立 librt（clock_gettime 等已并入 libc）。
3. **-lm 链接顺序**：simh 使用 fmod/log/exp/cos/sin/sqrt，`-lm` 必须位于源文件之后，
   通过 `LDFLAGS="-lm"` 传递。
4. **-D_GNU_SOURCE 保留**：musl 需此宏暴露 strncasecmp/usleep 等少量扩展。
5. **-fcommon 必需**：simh V3.8-1 依赖 gcc 历史默认的 common-symbol 合并
   （`altairz80` 的 `intr`、`ibm1130` 的 `sim_vm_init` 为 tentative definition）；
   clang 默认 `-fno-common`，链接期报 duplicate symbol。
6. **BIN/ 目录缺失**：源码 zip 携带的空 BIN/ 在解压时丢失，makefile 直接写 BIN/
   却不创建目录，需在 build() 中 `os.makedirs(<source>/BIN, exist_ok=True)`。
7. **strip_root=False**：源码 zip 含 44 个顶层条目，无单一根目录。
8. **无 install 目标**：package() 直接把 BIN/ 下 26 个二进制复制到 `bin/`。
9. **ELF 签名**：OHOS 内核要求可执行文件签名，package() 内（仅 os==OHOS）对
   `bin/` 下每个二进制执行 `llvm-objcopy --remove-section .codesign` +
   `binary-sign-tool sign -selfSign 1 -inFile X -outFile X`；工具不存在时跳过并告警
   （本机/CI 交叉环境无该工具，由消费端/CI 补签）。
10. **交互式 CLI**：simh 命令行非 `-` 参数被当作脚本文件名打开；`quit` 匹配
    命令表的 `QUIT`（`scp.c` 第 529 行 `{ "QUIT", &exit_cmd, 0, NULL }`）→ 主循环
    退出 → `main` 返回 0。因此非交互退出用 stdin 传 `quit`，退出码为 0。

## 验证

### 本机前置验证（W4，2026-09-27，本机 = Windows/MSYS + DevEco OHOS SDK clang 15）

本机无 make，故用脚本复现 makefile 的编译/链接规则，以 OHOS SDK 的
`clang --target=aarch64-linux-ohos` 交叉编译 26 个目标：

```
$ python3 build_simh.py           # fcommon=True
ALL entries: 27, unique targets: 26
BUILT OK: 26/26
```

产物架构核验：`llvm-readelf -h BIN/*` → 26/26 均为 `ELF64 / AArch64`；
`pdp11` 的 `DT_NEEDED` 仅 `libc.so`（musl，无 librt 残留）。

对照实验（证明两处配方处理的必要性）：

| 实验 | 结果 |
|---|---|
| 去掉 `-fcommon` | 24/26 成功；`altairz80`（`intr`）、`ibm1130`（`sim_vm_init`）链接失败 duplicate symbol |
| 不预建 `BIN/` 目录 | 0/26，全部 `ld.lld: error: cannot open output file BIN/<sim>` |

源码归档校验：SHA256 = `4fe294fa5285b1d6d0bd69f60889c00e518ce2be5f00abc2bd4adfa8daa85b06`，
经 `curl` 下载实测一致；归档为 ZIP、44 个顶层条目。

### 未执行 / 待补

- **本机 conan create 未执行**：本机无 Conan 与 GNU make，无法运行完整
  `conan create`。已用上述等价交叉编译 + 源码级行为核对代替，**不视为 CI 通过**。
- **test_package 未在本机实际运行**：交叉编译产物为 aarch64-ohos ELF，本机
  Windows 无法执行；`-q`/`quit`/banner 行为经源码核对确认（`scp.c`）。
- **真机 shadow CI 本轮未执行**：未拿到真机空闲窗口（真机测试单包排队）。
  历史 notes 中曾记录的 2026-09-19 真机结果本轮无法复现/证实，故不沿用，改为待补。
- 上游无测试套件：`make -n check` 无该目标，源码树无测试文件。

### HarmonyOS PC 真机 shadow CI 结果（2026-09-27）

隔离 job：`simh-3.8.1-shadow-20260927-134801`（设备侧 `ohos-test-runner.sh`，
命令 `zsh ci/conan/build_and_test.sh archives/s/simh/3.8.1`）。运行 3 分钟，exit 0。

```
-build: make CC="/data/service/hnp/bin/clang -std=c99 -U__STRICT_ANSI__ -O2
       -D_GNU_SOURCE -fcommon -I." LDFLAGS="-lm" -j1        # 26/26 目标编译链接成功
simh/3.8.1: package(): Packaged 27 files                     # 26 二进制 + licenses/LICENSE
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L1e: Negative test confirmed — test genuinely depends on simh  # R34 破坏性反向验证通过
L2_RESULT=pass: <26 个模拟器> --version OK
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
Build Summary: Total 1 / Success 1 / Failed 0 / exit 0
```

test_package（消费端）：`SIMH consumer smoke test: 26/26 assertions passed`
（26 个模拟器均打印 banner 并以 quit 干净退出）。

设备端实证（job 的 conan package 目录）：

- `bin/` 26 个二进制 + `licenses/LICENSE`；
- `readelf` 头：ELF class 2（64 位）、machine 183（AArch64）；
- 直接运行 `printf 'quit\n' | bin/pdp8` → 输出 `PDP-8 simulator V3.8-1` / `Goodbye`，rc=0；
- 签名分支实际执行（设备存在 `/data/service/hnp/bin/binary-sign-tool`，
  日志无 "skipping OHOS ELF self-signing" 告警）。

> 注：L2 原预判为 warn（认为 simh 不认 `--version`），实测 26 个模拟器
> `--version` 均返回 0，故实际为 pass。simh 的 `get_switches()` 接受任意字母开关，
> `-version` 被当作开关解析后进程正常退出。

## 源码归档

- URL：http://simh.trailing-edge.com/sources/archive/simhv38-1.zip
- SHA256：4fe294fa5285b1d6d0bd69f60889c00e518ce2be5f00abc2bd4adfa8daa85b06
- 元数据位于 `conandata.yml`（`sources.url` / `sources.sha256`）。

> 说明：早前草稿曾将 URL/SHA256 内联在 conanfile.py 以规避 CI pre-download 的
> `BUILD_DIR: parameter not set`。经核对当前 `ci/conan/build_and_test.sh`，
> pre-download 段已改为 `BUILD_DIR="${BUILD_DIR:-${REPO_ROOT}/.build-cache}"`
> （有默认值），该缺陷已不存在，故回归项目标准（conandata.yml + conanfile 读
> `self.conan_data["sources"]`），与 open-simh/3.12-3 等同类包一致。
> 该 URL 域名不在 CI 镜像重写白名单内，pre-download 走单 URL 直接下载路径。

## 交接说明

- issue 编号：待补（任务下达时未提供明确 issue 编号，本机前置适配先行）。
- 分支：`feat/simh-3.8.1`（worktree `D:\harmonyos\worktrees\simh`）。
- 真机 shadow CI：**已执行并通过**（2026-09-27，命令见上）。
