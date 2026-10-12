# pd-zexy 2.4.4 适配笔记

## 编译环境

| 项 | 值 |
|----|-----|
| 宿主 | HarmonyOS（HongMeng Kernel 1.13.0, aarch64） |
| 工具链 | OHOS SDK clang 15（target `aarch64-unknown-linux-ohos`），内置 |
| 构建系统 | 上游随源码 vendored 的 **pd-lib-builder 0.7.0**（`Makefile.pdlibbuilder`） |
| Conan profile | `ci/conan/profiles/ohos-aarch64`（`os=OHOS` 6.0 / `arch=armv8` / clang 15 / Release） |
| 编译期依赖 | `puredata/0.54.1`（头集在 `include/pd`；`libpd` 包不含内部头，不可用于编译） |
| 测试依赖 | `puredata/0.54.1`（其 `bin/pd` 作为上游回归套件的宿主） |
| 补丁 | **0**（未改上游任何源文件） |
| 状态 | published |

构建命令（配方 `build()` 内等价形态）：

```
make -j1 CC="<clang from tools.build:compiler_executables>" \
         PDINCLUDEDIR="<puredata package>/include/pd" with-lpt=no
```

89 个 `.c` → **单一** `zexy.pd_linux`（350528 B，ELF shared object，aarch64）。

## 问题清单

### #1 `ioperm` 未解析符号 —— 一个符号让整库不可加载（阻断级，本版本核心）

- **现象**：构建、链接、安装全部 `rc=0`，但宿主 `dlopen` 时报
  `Error relocating ./zexy.pd_linux: ioperm: symbol not found`；上游回归套件 36 项
  首跑 **13 PASS / 19 FAIL / 4 XFAIL**（失败的 19 项里绝大多数与并口毫无关系）。
- **根因**：zexy 用 `$(CPP)` 探 `<sys/io.h>` 是否存在来决定是否编译并口对象（`src/lpt.c`）。
  OHOS sysroot **装了**该头（内核 uapi 侧），但 **musl 不提供** `ioperm`/`inb`/`outb` ——
  探针假阳性。x86 专属对象被链进**同一个** `zexy.pd_linux`；共享对象的未定义符号在链接期
  被放行，直到 `dlopen` 全量重定位时才爆炸 → **单产物库「一坏全坏」**，库里约 90 个类全废。
- **修复**：使用上游自带开关 `with-lpt=no`（→ `-DZ_WANT_LPT=0`），**零补丁**。
- **验证**：`nm -uD zexy.pd_linux | grep -xE 'ioperm|iopl|inb|outb'` → **0 行**；
  上游回归 **32 PASS / 0 FAIL / 4 XFAIL**；`conan create` `rc=0`。

### #2 上游回归套件的补丁参数必须是**相对路径**（否则假失败）

- **现象**：test_package 首轮用绝对路径把补丁喂给 `tests/testrunner.sh`，`tests/absgn~/abs.pd`
  报 `error: abs: can't load abstraction within itself`，套件 3/36 FAIL —— 而同日手工跑
  （相对路径）是 0 FAIL。
- **根因**：该补丁里的 `abs` 抽象名在**绝对路径**下被 pd 解析成补丁文件自身。
  与被测库无关，纯路径形态差异（实测同一产物：绝对 FAIL=1 / 相对 FAIL=0）。
- **修复**：驱动脚本 `cd "$STAGE"` 后用 `find tests -mindepth 2 -name '*.pd'`（相对路径），
  等价上游 `make check` 从源码根收集补丁的形态。
- **验证**：同一产物、同一宿主，相对路径 32 PASS / 0 FAIL / 4 XFAIL。

### #3 上游回归套件依赖的非 `.pd` 数据必须随包分发

- **现象**：`package()` 只按 `*.pd` / `*.sh` 收集时，`msgfile/loading`、`msgfile/loadingCR`
  两例失败（缺参考数据文件）。
- **修复**：按扩展名整树收集（`*.pd` / `*.txt` / `*.sh` / `*.bat`），使
  `tests/msgfile/*.txt`、`tests/runtests.bat`、`tests/README.txt`、`tests/testtests/README.txt`
  以及 `abs/alias`（无扩展名）、`reference/{0.INTRO.txt,test.mtx}` 一并入包。
- **验证**：包内 `tests/` 47 个文件（= 源码树 47）、`abs/` 51、`reference/` 78、根级 15。

### #4 `conandata` 的 `sources` 须按 `self.version` 取键

- **现象**：`source()` 首版写成 `get(self, **self.conan_data["sources"], ...)`，报
  `get() got an unexpected keyword argument '2.4.4'`。
- **修复**：`get(self, **self.conan_data["sources"][self.version], strip_root=True, filename="v2.4.4.tar.gz")`。

### #5 编译器取值（同族经验，pd-lib-builder 通用）

`self.conf.get("tools.build:compiler_executables")` 在本仓 conan 基线（2.29.1）+ OHOS profile 下
是一个 **dict**，没有 `:c` / `:cpp` 子键 —— 须用 `check_type=dict` 读整表再取 `"c"`，
并保留 `or "clang"` 兜底（R33：不得依赖只在开发者会话里存在的 `${CC}`）。

## 验证结果

| 项 | 结果 |
|----|------|
| 构建（`make -j1`，89 `.c`） | ✅ `rc=0`，产物 350528 B |
| 符号层（`ioperm` 族） | ✅ 0 行（`nm -uD` 精确计数） |
| 上游回归套件（36 项） | ✅ **32 PASS / 0 FAIL / 4 XFAIL**（4 项 XFAIL 为上游预期失败） |
| `conan create`（W3 本地 CI） | ✅ `rc=0`，test_package 内实跑上游全套并断言 `FAIL==0 && TOTAL>=36` |
| 产物动态依赖 | `NEEDED=libc.so`，`RUNPATH=$ORIGIN`（自包含） |
| 补丁 | 0 |

## 知识沉淀

本版本暴露的缺口（**平台头探针假阳性 → 单产物库整体不可加载**）已沉淀为知识条目草稿
`knowledge/drafts/E998-draft-B183-pd-external-unresolved-symbol.kv` +
`knowledge/doc/E998-pd-external-unresolved-symbol.md`，与同族条目
（pd-vbap：pd-lib-builder 无 `cc` / 头集缺失 / musl 符号作用域，属「构建不起来」）
互补：本条覆盖「构建成功但产物整体不可加载」。
---

**编译结束**: 2026-10-01 20:50
**最终状态**: published
