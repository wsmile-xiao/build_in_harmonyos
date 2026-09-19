# rvvm 0.6 Makefile override MAKEFLAGS 覆盖命令行 -j1 的规避

## 问题

rvvm 0.6（上游 `Makefile`）在 OHOS shadow CI 上适配时，若在 conanfile.py 里按
R9 惯例传 `make -j1 lib all`，构建日志显示仍然并行编译，存在在 OHOS 上触发
FIFO jobserver 限制（E074）卡住/失败的风险。

## 根因

RVVM 的 `Makefile` 内含强制并行逻辑：

```make
JOBS ?= $(HOST_CPUS)
override MAKEFLAGS += -j $(JOBS)
```

- `JOBS ?= $(HOST_CPUS)`：命令行未传 `JOBS` 时，`JOBS` 默认等于 `nproc`。
- `override MAKEFLAGS += -j $(JOBS)`：无论命令行传什么，都把 `-j $(JOBS)`
  **追加**进 `MAKEFLAGS`。

命令行 `make -j1` 会让 `MAKEFLAGS` 先含 `-j1`，随后被上述 `override` 追加
`-j $(JOBS)`；GNU make 解析时**最后一个 `-j` 生效**，于是最终仍以 `nproc`
并行，`-j1` 形同失效。

## 修复方案

不传 `-j1`，改传 Makefile 自定义的并行度变量，让 `override MAKEFLAGS` 里
展开成单线程：

```python
# conanfile.py build()
self.run(
    "make lib all "
    f"CC={cc} AR={ar} "
    "BUILDDIR=build BINARY=rvvm JOBS=1 "
    "USE_FB=0 USE_SDL=0 USE_XSHM=0 USE_JNI=0 USE_TAP_LINUX=0"
)
```

`JOBS=1` 覆盖 `JOBS ?=`，于是 `override MAKEFLAGS += -j 1`，最终并行度为 1，
满足 R9（单线程）。

## 验证

- rvvm 0.6 OHOS shadow CI（run id `codex-0.6-rvvm-0.6-shadow-20260916-conan-20260916-194144-29838`）：
  exit code 0，`make lib all` 全源编译通过，test_package 通过，L0–L5 全 pass。
- 日志确认编译器为 clang 15.0.4 / arm64，`JOBS=1` 生效后未出现并行构建或
  FIFO jobserver 报错。

## 适用边界

- 适用于 **Makefile 型** 项目，且其 `Makefile` 用 `override MAKEFLAGS` 强制
  `-j$(JOBS)` 或 `JOBS ?= nproc` 模式（RVVM 为典型实例）。
- 变量名以实际 `Makefile` 为准（可能是 `JOBS`、`NJOBS`、`NPROC` 等），改前先读
  `Makefile` 确认；并非所有 Makefile 都定义了这类并行度变量。

## 查重结果

| 来源 | 命中 | 关联 |
|------|------|------|
| knowledge/graph/ E074 | 命中 | make -j FIFO jobserver 卡住 → `-j1`（假设 -j1 生效） |
| knowledge/drafts/ E333-draft | 命中 | 仓库 Makefile 模板统一 `-j1`（假设 -j1 生效） |
| knowledge/graph/ E283 | 命中 | Conan library 包 shared 选项契约（与本条无关，rvvm 另一处修复） |
| knowledge/drafts/ | 无 | 无"override MAKEFLAGS 覆盖命令行 -j1"既有条目 |

**新增价值**：E074/E333 都假定 `make -j1` 能生效；本条揭示 `override MAKEFLAGS`
会让命令行 `-j1` 被覆盖失效，必须改传 Makefile 自定义并行度变量（`JOBS=1`），
是该坑的下一层、未被覆盖的机制。

## 非适用范围

- 不使用 `override MAKEFLAGS` 强制并行的 Makefile：直接 `-j1` 即可（E074 常规解法）。
- CMake/Meson 项目（其并行度由各自生成器控制，不经过 `MAKEFLAGS` 覆盖机制）。

## 作者

- AtomCode (GLM-5.2)
- 来源：rvvm 0.6 OHOS shadow CI 适配（2026-09-16）
- 状态：DRAFT
