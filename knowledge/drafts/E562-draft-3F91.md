# E562 — Meson 项目 CI 专杀：native file 未声明 ar 且 worker PATH 无 llvm-ar

- 触发实例：c-stdaux 1.6.0 适配（PR !8549，任务 #6167），CI 构建 #40850（`archives/c/c-stdaux/1.6.0`）
- 状态：草稿，拟纳入正式知识库

## 可复现症状与稳定错误签名

c-stdaux 1.6.0（header-only，无任何库目标）本地 `conan-verify` 全绿，CI 恒失败于 `conan create` 的 `meson setup`：

```text
C compiler for the host machine: /data/service/hnp/bin/clang (clang 15.0.4 ...)
../meson.build:5:0: ERROR: Unknown linker(s): [['llvm-ar']]
The following exception(s) were encountered:
Running `llvm-ar --version` gave "[Errno 2] No such file or directory: 'llvm-ar'"
ERROR: c-stdaux/1.6.0@ohpcd/stable: Error in build() method, line 63
	meson.configure()  ConanException: Error 1 while executing
```

稳定签名：`Unknown linker(s): [['llvm-ar']]`，出现在 **meson setup 的编译器探测阶段**（任何 target 编译之前）。

## 根因与最小复现

Conan `MesonToolchain` 生成的 `conan_meson_native.ini`，`[binaries]` 段只写 c/cpp 的绝对路径（来自 profile 的 `tools.build:compiler_executables`），**不写 ar**。meson setup 在为 C 工具链做编译器探测时需要探测静态归档器，按裸名 `llvm-ar`/`ar` 逐个尝试：

- 本地设备 PATH（`~/.local/bin`、`~/.harmonybrew/bin`）有 ar → 探测成功 → 全绿；
- CI worker PATH（`/data/app/bin:/system/bin:/system/sbin:/vendor/bin:~/.local/bin`）没有 → setup 即失败。

最小复现：在 PATH 不含 ar 的环境里，对任一 MesonToolchain 配方执行 `meson setup`（无需任何库目标，header-only 同样触发——失败在探测阶段，与产物无关）。

## 已尝试方案（含失败）

1. 仅依赖 profile 的 compiler_executables（clang 绝对路径）→ ❌ ar 不在 native file，worker PATH 又没有。
2. 在 [binaries] 注入 `ar = '/data/service/hnp/bin/ar'`（与 clang 同目录，bstring 先例同路径）→ ✅ CI 通过。

## 最终方案与验证

- `generate()` 中 `tc.generate()` 之后对 `<generators_folder>/conan_meson_native.ini` 做精确替换：

```python
marker = "[binaries]\nc ="
if marker not in content:
    raise ConanInvalidConfiguration("meson native file layout changed")
content = content.replace(
    marker, "[binaries]\nar = '/data/service/hnp/bin/ar'\nc =", 1
)
```

- 锚点不存在必须 raise（防 native file 格式变更后静默失效）。
- 验证：修复提交 a32a39d266 后本地 conan-verify RC=0，CI 校验通过（!8549，02:42，健康 worker）。bstring/1.0.3（已合入）为同路径先例。

## 适用边界与反例

- 适用于所有 Conan MesonToolchain 项目在干净 CI worker 上的 setup；本地验证永远测不出本问题（PATH 二象性），必须 CI 实证。
- 与 E012 同族不同通道：E012 是 autotools/make 场景的 ar 环境变量方案；与 E296（Windows cross file 路径）不同平台。
- 反例提示：若 CI worker 恰好有裸名 llvm-ar（未来镜像更新），问题消失但注入仍无害——绝对路径注入是幂等防御。

## 查重与新增价值

- `knowledge/graph/index.tsv` grep `llvm-ar`：E012（autotools/make 的 ar 环境变量方案，签名 `ar command not found/invalid option`）、E236（libtool .la 与 llvm-ar）、E296（Windows cross file）、E385（cargo cmake overlay）——均与本条目的"meson setup 探测阶段 + native file 注入"签名与通道不同；引擎匹配 E012 为最近邻，核对后根因层面互补。
- 新增价值：把"本地全绿 CI 恒红"的强二象性陷阱、其专属签名与 MesonToolchain 下的确定性注入处方固化为可匹配条目，并显式关联 E012 供引擎跨通道召回。
