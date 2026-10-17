# DRAFT-libmad-0.15.1b-clang-gcc-only-optimization-flags：configure 内嵌 GCC 专属优化 flag 兼容处理

> Contributor: pc6-5 (OH executor) | Status: Draft | Updated: 2026-09-07
> Source: libmad 0.15.1b HarmonyOS PC 适配（task libmad-0.15.1b-r01-pc6-5-20260906T152808Z）
> 本文件与 `DRAFT-libmad-0.15.1b-clang-gcc-only-optimization-flags.kv` 配对，stem 相同，
> 字段（主题 / error_signature / root_cause / solution / validation / 适用边界）相互对应。

## 现象

libmad 0.15.1b（2004 年 autotools 项目）在 OHOS PC clang-15 工具链下 configure 成功后，
make 编译时 clang 报未知选项。configure 生成的 optimize 变量包含一串 GCC 3.x 时代
专属 flag：`-fforce-mem -fforce-addr -fthread-jumps -fcse-follow-jumps
-fcse-skip-blocks -fexpensive-optimizations -fregmove -fschedule-insns2`，
clang 一律不识别。

```text
cc1: error: unrecognized command-line option "-fforce-mem"
cc1: error: unrecognized command-line option "-fexpensive-optimizations"
```

## 根因（error_signature / root_cause）

- GCC 2.95/3.x 时期的 configure.ac 在 `optimize` 变量里硬编码了这些"力度提示"flag，
  期望 GCC 内联汇编/调度优化。
- clang 从未支持这些历史 flag（无等价实现），直接拒绝；且该报错不能被
  `-Wno-*` 类选项压制（不是 warning 升级，是 unknown option）。
- 表面看像工具链故障，实为 configure 向 CFLAGS 注入不支持的 flag。

## 方案（solution / rec_approach）

在 Conan recipe 的 `build()`（或等价补丁步骤）中、`configure` 运行**之前**，
用 `replace_in_file` 逐行删除 configure 内形如
`optimize="$optimize -fforce-mem"` 的行：

```python
for flag in ['-fforce-mem', '-fforce-addr', '-fthread-jumps',
             '-fcse-follow-jumps', '-fcse-skip-blocks',
             '-fexpensive-optimizations', '-fregmove', '-fschedule-insns2']:
    replace_in_file(self, configure,
                    '    optimize="$optimize {}"\n'.format(flag), '')
```

要点：
- 只删 clang 实际拒绝的 flag；`-O2 -fPIC` 等公共 flag 必须保留。
- 不必整体关闭优化，也不用手动改写 CFLAGS 覆盖 configure。
- 具体 flag 集合随项目年代/版本而异，逐项目 grep 确认。

## 验证（validation）

- 删除后 `./configure --enable-static --disable-shared` + `make -j1` 无未知选项报错。
- conan create（OHOS aarch64 profile）全链路通过；test_package 2/2 通过。
- 专项解码测试输出 1152 PCM 样本/帧，解码正确。

## 适用边界（boundary / affected_scope）

- 从 GCC 2.95/3.x 时代保留下来的 autotools 项目，移植到 clang 系工具链
  （OHOS PC clang-15 及各类 clang 交叉工具链）。
- 典型：2000 年代初期的音频/DSP/媒体库（libmad、minimad 一族）。

## 查重差异

- **exact_duplicate**: false — 全库检索 fforce-mem/fexpensive-opt/fregmove 0 命中。
- **causal_duplicate**: false — 无同根因既有条目。
- **trigger_overlap**: false — E063（-Werror 升级）触发面不同。
- **solution_overlap**: false — 无同类 configure flag 剔除方案。
- **combination_novelty**: true — 与 E205（config.guess/config.sub OHOS 识别）组合覆盖
  "旧 autotools 项目 OHOS 适配"完整链路。
- **boundary_novelty**: true — 边界为"clang 不识别历史 GCC flag 且不可用 -Wno 压制"。
- **test_migration_novelty**: true — 无既有测试迁移入口。

关系：`similar_to= E063, E205`；`caused_by= none`；`prerequisite_of= none`；
`conflicts_with= none`。