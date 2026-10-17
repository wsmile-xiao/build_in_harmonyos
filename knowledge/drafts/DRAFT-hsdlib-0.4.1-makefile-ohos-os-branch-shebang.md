# ═══ Draft knowledge entry — Makefile 项目在 OHOS 的平台识别与 SHELL 适配（uname -s=HarmonyOS + 无 /bin/bash）═══
# Timestamp: 2026-09-21
# Software: hsdlib 0.4.1（任何使用裸 Makefile 平台检测 + 硬编码 SHELL 的 C/C++ 库）
# Gate: make build / conan create / W3 本地 CI
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-hsdlib-0.4.1-makefile-ohos-os-branch-shebang
severity: 2
category: platform|make|ohos
trigger_tool: make
phase: configuration|compilation

## 错误特征（error_signature）

```
make: /bin/bash: No such file or directory ... Error 127
Creating shared library lib/hsd.        ← 无 .so/.a 扩展名
```

## 根因（root_cause）

OHOS（HarmonyOS PC, aarch64）平台两个独立差异叠加在同一 Makefile：

1. `uname -s` 返回 `HarmonyOS` 而非 `Linux`。裸 Makefile 的
   `ifeq ($(OS),Linux)` / `ifeq ($(OS),Darwin)` / Windows 分支全部不命中，
   导致 `SHARED_LIB_EXT`/`SHARED_LIB_PREFIX`/`STATIC_LIB_EXT` 变量为空，
   产物名变成 `lib/hsd.`（无扩展名）。
2. OHOS 无 `/bin/bash`（bash 位于 `/data/service/hnp/bin/bash`，`/bin/sh` 存在）。
   Makefile 顶层 `SHELL := /bin/bash` 硬编码绝对路径导致每个 recipe 报
   `make: /bin/bash: No such file or directory`（Error 127）。

## 修复（rec_approach: patch-makefile-ohos-os-branch-and-shebang）

```make
# ① OS 分支：Linux 与 HarmonyOS 统一识别（so/a/lib 前缀一致）
ifeq ($(filter Linux HarmonyOS,$(OS)),$(OS))
    ifeq ($(OS),Linux)
        SHARED_LIB_EXT     := so
        SHARED_LIB_PREFIX  := lib
        STATIC_LIB_EXT     := a
        EXE_EXT            :=
        IS_DEBIAN := $(shell command -v apt-get >/dev/null 2>&1 && echo 1 || echo 0)
    endif
    ifeq ($(OS),HarmonyOS)
        SHARED_LIB_EXT     := so
        SHARED_LIB_PREFIX  := lib
        STATIC_LIB_EXT     := a
        EXE_EXT            :=
        IS_DEBIAN := 0
    endif
endif

# ② SHELL 回退（bash 存在用 bash，否则 /bin/sh；OHOS /bin/sh 实测支持 -o pipefail）
SHELL := $(shell command -v bash 2>/dev/null || echo /bin/sh)
.SHELLFLAGS := -e -o pipefail -c
```

## 验证（hsdlib 0.4.1 实测）

- `make build`：产物 `lib/libhsd.a` + `lib/libhsd.so`（补丁前为 `lib/hsd.`）
- `make test`：160/160 源码声明用例通过（166 条 Running test，166 PASS / 0 FAIL）
- `make test-aarch64`（AUTO/SCALAR/NEON/SVE）：664 PASS / 0 FAIL
- `conan create` 干净构建 + test_package 消费者测试（6 公开 API）与鸿蒙专项测试（后端调度）全 PASS
- W3 本地 CI（setup.sh + build_and_test.sh）通过

## 适用范围（affected_scope）

- 所有裸 Makefile（非 autotools/cmake/meson）构建、内部用 `uname -s` 做 OS 分支判断、
  或硬编码 `SHELL := /bin/bash` 的 C/C++ 库（OHOS PC arm64）。
- 同类知识：E160（config.guess 无法识别 HarmonyOS，autotools 触发面）、
  E140（CMake CMAKE_SYSTEM_NAME 未定义 OS_LINUX）、E165（脚本 shebang bad interpreter）。
  本条目覆盖 E160/E140 未覆盖的**裸 Makefile** 触发面，并与 E165 的脚本 shebang
  区分（Makefile SHELL 变量 vs 脚本解释器行）。

## 关键原则（principles）

- OHOS 平台语义与 Linux 不完全等价：`uname -s`=HarmonyOS、无 `/bin/bash`。
- 裸 Makefile 平台适配必须同时核对 OS 分支与 SHELL 两处。
- conan.tools.files.copy() 保留匹配文件相对目录结构：package() 的 src 需指向子目录
  + 无前缀扁平模式，避免 include/include、lib/lib 双重嵌套
  （hsdlib 实测：copy("lib/*.a", src=source_folder, dst=package/lib) → p/lib/lib/libhsd.a）。

## 证据（evidence）

- `archives/h/hsdlib/0.4.1/reports/conan-create.log`（G2 干净构建，含补丁应用）
- `archives/h/hsdlib/0.4.1/reports/upstream-test-ledger.md`（160/160 双口径台账）
- `archives/h/hsdlib/0.4.1/reports/test-report.md`（消费者 + 鸿蒙专项测试）
- `archives/h/hsdlib/0.4.1/reports/baseline-isolation-audit.md`（W3 基线隔离复验）
- `archives/h/hsdlib/0.4.1/patches/0001-Makefile.patch`（补丁本体）
