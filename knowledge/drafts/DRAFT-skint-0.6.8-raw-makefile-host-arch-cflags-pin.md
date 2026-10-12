# DRAFT-skint-0.6.8: 手写 makefile 的“构建机 uname 架构嗅探 + 默认 PREFIX 编入绝对路径”

Status: DRAFT
Source: skint 0.6.8（false-schemers/skint，tag v0.6.8）
PR: 【知识库扩展】feat(skint): 0.6.8 适配 HarmonyOS PC（分支 feat/skint-0.6.8）

## 相关既有条目

撞库命令与结果（2026-10-02）：

```
python3 scripts/ohc-run.py engine "uname -m 自动 -D NAN_BOXING 交叉编译 CFLAGS"      -> E036（Python get_platform 含空格）
python3 scripts/ohc-run.py engine "构建机架构 决定目标产物 PREFIX 绝对路径 烤入 ELF"  -> E296（Conan Meson helper 从 Windows 构建机推导 prefix）
python3 scripts/ohc-run.py engine "makefile CFLAGS 命令行覆盖 不可复现"              -> E063（-Werror 类别）
grep -Ein "uname|nan_boxing|命令行变量|build host" knowledge/graph/index.tsv        -> 仅 E007（config.guess/triplet）、E036（uname 空格）
grep -REil "nan_boxing|uname -m|构建机" knowledge/doc/                              -> E518/E543/E359/E517（git RUNPATH、flex/bison、HOSTCC 映射、codesign），均不覆盖
```

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E007 | autotools `config.guess/config.sub` 识别不出 HarmonyOS 三元组（`--build/--host` 绕道族） | E007 是 **autotools 三元组识别**；本条是**手写/GNU makefile 用宿主 `uname` 推导编译参数**，产物本身能编出来，错的是参数量值（架构宏 + 绝对路径） |
| E036 | `uname -r` 含空格导致 Python `get_platform()` 路径解析失败 | E036 是**运行时字符串解析**；本条是**编译期参数取值**，且后果是产物语义分叉 + 不可重定位 |
| E296 | Conan Meson helper 从 Windows 构建机推导 install prefix（Meson/Windows 场景） | 同属“构建机状态泄漏进目标”，但 E296 在 **Conan helper + Meson** 层；本条在**上游 makefile 自身**的 `$(shell uname)`/`PREFIX` 层，且叠加了架构宏与 ELF 绝对路径两条后果 |
| DRAFT-E640 | OHOS `uname -s` 返回 `HarmonyOS` → 按 OS 名分支的 makefile 落空（目标侧平台名检测） | E640 是**目标侧平台名**不匹配；本条是**构建侧架构**误代入 + `PREFIX` 派生路径。两者共享“make 命令行变量覆盖”这一手法，失效面不同 |
| DRAFT-E687 | 纯 make 包用 make 命令行钉 CFLAGS/CXXFLAGS/LIBS，防 **CI 环境 flags 泄漏** | 动机不同：E687 防的是环境变量污染，本条防的是**构建机/目标机语义分叉**与构建机绝对路径编入 |
| E063 / E099 / E401 | `-Werror` 类别 / b2 平台检测 / libm 舍入 | 与本条问题域无关，仅作检索留痕 |

结论：现有正式条目与草稿均未覆盖“手写 makefile 宿主探测派生 CFLAGS + PREFIX 绝对路径编入”这一模式，可独立申报；相近条目已填入 `.kv` 的 `similar_to`。

## Scope

适用：

- 手写 / GNU makefile 项目，用 `$(shell uname -m)`、`$(shell uname -p)` 之类**宿主探测**推导 `ARCH` 并据此追加架构编译参数；
- 该 makefile 同时把默认 `PREFIX`（通常 `/usr/local`）拼进编译宏（如 `-DLIBDIR=$(PREFIX)/share/<pkg>/lib`）；
- 需要**交叉编译**到 HarmonyOS PC（aarch64-linux-ohos）等目标。

不适用：autotools/CMake/Meson（用 Conan 工具链类解决）；参数全部来自命令行或配置文件的 makefile；宿主探测只用于日志展示、不进入编译命令行。

## Symptom

在本机 macOS（arm64）上交叉编译 skint 0.6.8（目标 aarch64-linux-ohos），构建日志里出现的是**构建机**的架构判断与构建机绝对路径：

```
version is 0.6.8
prefix is set to /usr/local
clang is detected
ARM_64 architecture is detected                      # ← 构建机 uname，不是目标机
clang -O3 -DNDEBUG -DLIBDIR=/usr/local/share/skint/lib -D NAN_BOXING -c -o n.o n.c
```

两条后果：

1. `-D NAN_BOXING` 是否启用由构建机决定。skint 的 makefile 按 `uname -m` 命中
   AMD64/ARM64/POWER64/RV64 才追加它（NaN-boxing 依赖 48 位地址空间的对象表示）。
   本机 macOS arm64 会打开；真正的 OHOS aarch64 上 `uname -m` 是 `aarch64`，走不到任何
   分支、反而不打开 → 同一配方在两台构建机产出**语义不同**的二进制，CI 与本地不一致且
   无法复现。
2. `-DLIBDIR=/usr/local/share/skint/lib` 是 makefile 用默认 `PREFIX ?= /usr/local`
   拼出的**构建机绝对路径**，会被编进目标 ELF；包搬进 Conan 包目录后运行时默认库搜索
   路径必然失效，包不可重定位。

## Root Cause

```make
UNAME := $(shell uname -m)
ifeq ($(UNAME),x86_64)
  ARCH = AMD64
endif
ifeq ($(ARCH),ARM64)
  CFLAGS += -D NAN_BOXING      # ← 读的是构建机架构
endif
...
ifneq ($(wildcard lib/.),)
  CFLAGS += -DLIBDIR=$(LIBROOT)/lib   # ← LIBROOT=$(PREFIX)/share/...，PREFIX 默认 /usr/local
endif
```

- `$(shell uname -m)` 描述的是**执行 make 的机器**，交叉编译时与目标三元组无关；
- `PREFIX` 的默认值来自“装到本机 /usr/local”的传统假设，在 Conan 包里既不成立也不可重定位。

两者都不是编译器/平台缺陷，而是**构建参数把宿主状态泄漏进了产物**。

## Recommended Fix / Workaround

用 make 的**命令行变量**整体钉死（GNU make 中命令行变量优先于 makefile 内的 `=` 与 `+=`）：

```python
# conanfile.py build()
cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")
self.run('make -C "{src}" -j1 CC="{cc}" CFLAGS="-O2 -DNDEBUG" "./skint"'.format(src=src, cc=cc))
```

修复后实测编译行（skint 0.6.8 + OHOS SDK clang 15.0.4）：

```
<ohos-clang> -O2 -DNDEBUG -c -o n.o n.c
<ohos-clang> -O2 -DNDEBUG -o skint s.o k.o i.o n.o t.o -lm
```

宿主架构嗅探与 PREFIX 派生值均不再进入产物；外置库树改用 Conan `runenv_info` 注入
`SKINT_LIBDIRS`（运行期，保持可重定位），而不是编入 `-DLIBDIR`。

## Fallback

若同一份 makefile 必须继续支持本机构建，可打最小补丁让参数尊重外部传入
（例：`ARCH ?= $(shell uname -m)` 改为可被命令行覆盖的形态，或把 `CFLAGS +=` 换成
`CFLAGS ?=`），补丁走 `ohc-run.py refresh-patch --auto` 并保持可向上游提交（P005）。

## Forbidden Approaches

| 禁止写法 | 原因 | 后果 |
|---|---|---|
| 在 conanfile 里 `CFLAGS += "-D..."` 追加 | 追加压不住 makefile 内的宿主探测与 `PREFIX` 派生值 | 构建机决策与绝对路径照样进产物 |
| `sed -i` 直接改 makefile | 不可复现、重新解包即失效（R6/P003） | 改动不进补丁体系，后续构建悄悄退回宿主嗅探 |
| 用 `-Wno-*` 之类压制告警让构建“看起来通过” | 本条不是告警问题，产物语义已经分叉 | 掩盖真正的不可复现缺陷 |

## Verification

```bash
# 1) 交叉编译，检查编译行不再含宿主派生宏/路径
make -C <src> -j1 CC="<conf cc>" CFLAGS="-O2 -DNDEBUG" "./skint" 2>&1 | tee build.log
grep -E -- '-D NAN_BOXING|-DLIBDIR=/usr/local/' build.log && echo "STILL LEAKING" || echo "OK"

# 2) 产物可重定位（不再残留构建机绝对路径）
strings <target> | grep -c '/usr/local/share/skint'   # 期望 0

# 3) 产物 ABI 仍指向 OHOS
llvm-readelf -d <target> | grep NEEDED                # 期望仅 libc.so
```

## Prevention

- 适配前的依赖/构建预检里读一遍 makefile 的 `$(shell ...)` 与 `PREFIX`/`CFLAGS` 默认值；
  凡 `uname`/`hostname`/`which` 参与**编译参数**推导的，一律在配方里用命令行变量整体覆盖。
- `notes.md` 必须记录被压掉的宿主探测项（P006：CFLAGS 相关改动记为技术债并写清期望的上游修法）。
- 交叉编译产物做一次 `strings | grep` 构建机前缀的体检，作为可重定位性的最小门禁。

## References

- skint 0.6.8 上游 makefile：`https://github.com/false-schemers/skint/blob/v0.6.8/Makefile`
- 本仓归档：`archives/s/skint/0.6.8/{conanfile.py,notes.md,manifest.yaml}`
- 同族先例：`DRAFT-E640`（uname -s 平台名）、`DRAFT-E687`（命令行钉 flags）、`E296`（Conan helper 推导 prefix）
- 相关原则：P006（CFLAGS 改动记技术债）、P014（环境变量与构建系统语义冲突）
