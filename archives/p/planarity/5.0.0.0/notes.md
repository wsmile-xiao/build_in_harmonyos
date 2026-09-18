# planarity 5.0.0.0 适配笔记

## 编译环境
- 构建系统: autotools（源码包内已附带生成好的 `configure`，无需 autoreconf）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4（OHOS SDK，`/data/service/hnp/bin/clang`）
- 目标 profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS / os.version=6.0 / arch=armv8 / compiler=clang 15）
- 状态: built（conan-verify 通过；未经 release 流水线上传，故不是 published）

## 上游测试清点（R51 申报表）

| 口径 | 数量 | 取数命令 / 证据 |
|---|---|---|
| autotools 框架注册测试（`TESTS`） | **1** | `Makefile.am`: `TESTS = test-samples.sh` |
| `make check` Testsuite 汇总 | TOTAL **1** / PASS **1** / FAIL 0 / SKIP 0 | conanfile `build()` 内 `autotools.make(target="check")`，日志 `reports/conan-create.log` |
| 该测试程序内部驱动的比对项 | 40 项 = 16 条主结果比对 + 4 条二次结果比对 + 14 条图变换输出比对 + 6 条 `n8.mALL.g6` 全图批量命令 | `./planarity -test <samples>` 输出（安装树内 CLI 复跑），逐字存 `reports/upstream-planarity-test.md`（sha256 `76e9586762662f51…`） |
| 消费者断言（鸿蒙特有，**不进上游分母**） | **49** = 42（库 API）+ 7（CLI） | `test_package/test_planarity.c`、`test_package/test_cli.sh` |

**N 口径（同一统计单位，不混用）**：上游测试总数 **N = 1**，即 autotools 框架注册的唯一测试程序
`test-samples.sh`（`# TOTAL: 1` 机械可复算）；本次实际运行数 **N′ = 1**，通过率 1/1 (100%)。
`test-samples.sh` 内部调用的 `./planarity -test <dir>` 属于**该测试程序内部**的回归比对，
不是框架注册的第二个测试入口，按框架注册口径不重复计入分母；其逐项清单另列于
`reports/upstream-planarity-test.md`，避免"少报"疑虑。

## 编译步骤

```sh
# 1) 源码：GitHub Release 官方资产 planarity-5.0.0.0.tar.gz
#    sha256=8aa3958f92e3fbbc63815e5b6b454abe40889af5aa35da8306659c58ec16a2d0
# 2) 适配补丁（refresh-patch --auto 生成，见下节）
# 3) 配方构建（conan create，OHOS aarch64）
conan create archives/p/planarity/5.0.0.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
# conanfile.build() 内部：
#   ./configure --enable-static --disable-shared ...   （AutotoolsToolchain）
#   make -j1
#   make check -j1        # 上游测试套件（R51/W3 证据）
```

手工等价验证（设备原生，用于定位平台问题）：

```sh
perl "$MAIN_REPO/scripts/patch-autotools-ohos.pl" config.guess config.sub
sed -i 's/umask 077/umask 022/g' configure
./configure CC=clang CXX=clang++ --prefix=<prefix> && make -j1 && make check -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one` | GNU `config.guess` 无 HarmonyOS 分支；本机 `uname -s` = `HarmonyOS` 不匹配任何已知系统（知识库 **E007**） | 官方 `scripts/patch-autotools-ohos.pl config.guess config.sub` 打补丁，使 `config.guess` 输出 `aarch64-unknown-linux-ohos`（自检 4/5，`sh config.guess` 实测输出该三元组） |
| 2 | `./config.status[964]: can't create ./conf0lrpT9/subs1.awk: Permission denied` → `could not setup config files machinery` | `configure` 生成 `config.status` 时用 `(umask 077 && mktemp -d ./confXXXXXX)`；HMDFS 给新目录强制 setgid 且把属主映射为共享属主 `20001006`，落盘 `drwx--S---`，连创建者（euid 20020084）都不可写（知识库 **E011/E129**，`notes/device-facts.md` §一.10） | 补丁把 `configure` 内**两处** `umask 077` 改为 `umask 022`；生成的 `config.status` 自然继承 022，临时目录 `drwxr-s--x` 可写 |
| 3 | 库消费者测试首轮 7/34 断言失败（我方断言假设错误，非库缺陷） | 内存图 API 是 **1-based**（顶点 0 = NIL），而邻接表**文件**是 0-based 文本（flags 置 `GRAPHFLAGS_ZEROBASEDIO=16`）；`gp_TestEmbedResultIntegrity()` 成功路径返回与 `embedResult` **同值**（OK/NONEMBEDDABLE），不是恒 OK | 用探针程序实测真实返回值后改写断言：顶点用 1..N；完整性校验写成 `integrity == embedResult`。修正后 42/42 全过（见 `reports/`） |
| 4 | Conan L2 冒烟门禁报 `planarity: --version 和 --help 均失败` | 上游 CLI 只认单横线选项（`-h`/`-help`）；`--help` 落进 "Unsupported command line" 分支并返回 -1（实测 rc=255），`--version` 同理 | 补丁 `0001` 增加 `--help` 别名与 `--version` 单行输出；实测 `planarity --version` rc=0、`--help` rc=0，且 `-h`/`-test`/`make check` 行为不变 |

## 源码修改（patches/，均由 `refresh-patch --auto` 从编辑追踪器生成）

| 补丁 | 类型 | 内容 | 依据 |
|---|---|---|---|
| `0001-c-planarityApp-planarityCommandLine.c.patch` | portability | CLI 增加 GNU 惯例长选项：`--help`（等价 `-h`）与 `--version`（单行 `planarity <ver>`） | Conan L2 冒烟门禁依次尝试 `--version` / `--help`；上游只认单横线 `-h`/`-help`，实测 `--help` rc=255。先例：`archives/a/aa3d/1.0` 同因补 `--version`/`--help` |
| `0002-config.guess.patch` | portability | `config.guess` 增加 `HarmonyOS` 系统识别分支（输出 `aarch64-unknown-linux-ohos`） | E007；官方 `patch-autotools-ohos.pl` 产物。**只保留 POSIX shell 的 `*:HarmonyOS:*:*` case 分支**：官方工具另加的 `__OHOS__` LIBC 探针位于 `Linux|GNU|GNU/*)` 块内，该块仅当 `uname -s` 为 Linux/GNU 时进入，在本平台（`uname -s`=HarmonyOS）不可达，故删除以避免补丁引入平台宏（R8/PF5） |
| `0003-config.sub.patch` | portability | `config.sub` 增加 `ohos-linux` 三元组规范化 | E007；官方 `patch-autotools-ohos.pl` |
| `0004-configure.patch` | platform | `configure` 内两处 `umask 077` → `umask 022`（config.status 临时目录） | E011/E129；HMDFS setgid + 属主映射 |

补丁 apply 验证：对原始源码树 `patch -p1` 顺序应用 4 个补丁后，`c/planarityApp/planarityCommandLine.c` /
`config.guess` / `config.sub` / `configure` 与编辑后工作树**逐字节一致**（`cmp` 全 OK）；
补丁后 `sh config.guess` 实测输出 `aarch64-unknown-linux-ohos`。

> 全部 4 个补丁的新增行均**不含平台宏**（`__OHOS__`/`-D__OHOS__` 计数为 0），
> 走 POSIX 兼容写法（R8 / PF5）。

## 依赖版本

无外部依赖。`configure.ac` 仅 `AC_PROG_CC` / `AC_PROG_INSTALL` /
`AC_CHECK_HEADERS([ctype.h stdio.h stdlib.h string.h time.h unistd.h])`，全部为 libc 头文件；
W0 依赖清单 = `none`（`$TASK_DIR/w0-deps.txt`）。

## 验证结果

```text
# 上游测试（conanfile build() 内的 make check）
Testsuite summary for planarity 5.0.0.0
# TOTAL: 1
# PASS:  1
# SKIP:  0
# FAIL:  0
# ERROR: 0

# 消费者：库 API
ASSERTIONS: 42/42
ALL ASSERTIONS PASSED

# 消费者：CLI
CLI ASSERTIONS: 7/7
ALL CLI ASSERTIONS PASSED
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/planarity` | 命令行工具（平面性判定/嵌入/绘制/批量回归） |
| `lib/libplanarity.a`（默认 shared=False） | libplanarity 静态库（shared=True 时为 `libplanarity.so.4.0.0`） |
| `include/planarity/graphLib.h` + `include/planarity/c/graphLib/**` | 公共头文件（umbrella + 分层） |
| `lib/pkgconfig/libplanarity.pc` | pkg-config 元数据 |
| `share/doc/planarity/samples/` | 上游样例（`planarity -test <dir>` 的数据源） |
| `share/man/man1/planarity.1` | 手册页 |

## 注意事项

- **内存图 API 是 1-based**：`gp_GetVertexDegree(g, 0)` / `gp_AddEdge(g, 0, ...)` 对顶点 0
  无效（0 = NIL）。读入 0-based 邻接表文本后，公共 API 仍用 1..N 索引。
- `shared` 选项显式二选一（`--enable-static --disable-shared` / 反向），避免 libtool
  默认同时产出 `.a` 与 `.so` 造成消费者链接歧义。
- `package()` 删除 libtool `.la`（含构建期绝对路径，破坏可重定位性）。
- 构建固定 `make -j1`：HMDFS 拒绝 `mkfifo` 导致 make 的 fifo jobserver 打 EPERM 噪声
  （`notes/device-facts.md` §一.13），且共享设备需并发卫生。
- **消费者要运行包内 CLI 时必须 `self.requires(ref, run=True)`**：Conan 的 `VirtualRunEnv`
  仅在 `require.run` 为真时注入 PATH（`conan/tools/env/virtualrunenv.py`：
  `if require.run: _prepend_path("PATH", cpp_info.bindirs)`），而本包默认 `shared=False`
  → `package_type` 解析为 `static-library`，默认 `run=False` → 既不在 CMakeDeps 里保留
  `bin_paths`（`if require and not require.run: self.bin_paths = ""`），也不注入 PATH。
  只靠 `generators = "VirtualRunEnv"` 会拿到空环境（实测 `conanrunenv-*.sh` 的变量列表为空、
  `command -v planarity` 落空 → rc=127）。知识库 **E298** 的补充：它建议 VirtualRunEnv +
  `self.run(..., env="conanrun")`，但对"库包同时交付可执行文件"这一形态还需补 `run=True`
  （或像本包 test_cli.sh 那样显式传二进制绝对路径做兜底）。
