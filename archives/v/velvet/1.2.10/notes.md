# velvet 1.2.10 适配笔记

## 任务/包名/上游判定
- 任务名: velvetC++ 1.2.10（"C++" 为任务语言标注）
- 最终包名: velvet；上游: https://github.com/dzerbino/velvet，tag v1.2.10
- 候选排除: vitalight/Velvet（CUDA 布料模拟，最高 v0.6.1，无 1.2.10）、
  gobuffalo/velvet（Go）、intrnl/velvet（JS）等语言/版本均不匹配；
  仅 dzerbino/velvet 存在 v1.2.10 tag，唯一命中。

## 编译环境
- 构建系统: 上游手写 Makefile（无 configure）
- 编译日期: 2026-09-29
- 编译器: OHOS SDK clang 15.0.4（aarch64-linux-ohos，本地交叉验证）；
  macOS Apple clang 17（原生辅助验证）
- 状态: published（远程 OHOS CI #66602 真机全绿：conan create + 上游 5/5 + test_package U1-U5/H1 + L0/L1 门禁）

## 依赖预检（W0）
- 依赖: zlib/1.3.1.1 → `conan download zlib/1.3.1.1 -r=ohpcd --only-recipe` 成功（已发布）
- 注: ci/scripts/preflight_check.sh 在本机 bash 3.2 下因 $() 内嵌 heredoc 触发解析器
  限制报 syntax error（上游脚本问题，ci/ 为只读基础设施未修改），W0 改用 R35 手动
  conan download 口径完成。
- CI 能力矩阵: C toolchain ✅（gcc/clang/make 均有）；无需 Rust/Go/OCaml/flex/bison。
  fmtAuto 模式运行期依赖外部 gunzip（E402 已知 OHOS toybox gzip 支持短选项 -c -d）。

## 编译步骤
1. `make -j1 velveth velvetg CC=<conan conf c> CFLAGS="-Wall -I<zlib>/include" LDFLAGS="-L<zlib>/lib"`
   - 命令行覆盖 CFLAGS 同时剔除上游硬编码 `-m64`（aarch64 无意义，免补丁）
   - 显式目标跳过 `doc`（需要 pdflatex）
   - 不使用 BUNDLEDZLIB（third-party/zlib-1.2.3），链接系统 zlib
2. 上游测试（can_run 守卫，OHOS worker 原生执行）:
   `bash tests/run-tests.sh`（等价 make test；显式 bash 避免 /usr/bin/env 解析问题）

## 上游测试清点（三步法）
1. 构建入口: Makefile `test` 目标 → `cd tests && ./run-tests.sh`
2. 全包扫描: tests/（5 个 .t + run-tests.{sh,functions} + 数据）、
   data/（示例输入，无断言）、contrib/（第三方插件，各自独立项目，不计入）
3. 内容扫描: .t 内 cmp 断言与失败预期检查共 12 项
- 状态: A（正式 runner + case）。计数口径: **runner 原生 NUMTESTS=.t 脚本数=5**，
  全库统一（MANIFEST/notes/PR 表同一口径）。
- macOS 原生辅助验证（非 HarmonyOS 真机证据）: 5/5 通过；
  e2e 参考值 k=21 reads.fa.gz → contigs=6319, n50=44, total=355165。

## 鸿蒙特有测试（rule12）
- H1: test_package/test.sh 内 velveth→velvetg 完整组装 e2e（k=21，reads.fa.gz），
  校验 Sequences/Roadmaps 非空 + contigs.fa 非空含 FASTA 头。
  真实安装产物（conanrun PATH）→ 实际调用 → 功能结果校验。N=1。
- 上游 5 用例对安装产物原样重放：tests/*.t 硬编码 ../velveth 相对路径，
  测试工作目录按相同布局放置 shell 包装脚本 exec 真实 ELF
  （不复制/重命名 ELF，遵守 OHOS codesign 约束），上游测试脚本零修改。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `-m64` | x86 时代遗留，aarch64 无意义 | make 命令行覆盖 CFLAGS（免补丁） |
| 2 | default 目标含 doc 需 pdflatex | 上游默认值 | 显式构建 velveth/velvetg 目标 |
| 3 | preflight_check.sh 本机无法运行 | bash 3.2 对 $() 内 heredoc 的解析限制 | 手动 conan download 完成 W0（R35 口径） |
| 4 | CI checkout 失败：missing binary patch data（PR #14063 首轮） | GitCode PR diff 不携带二进制补丁，git apply 无法应用 corpus 内 6 个 .gz | corpus 改存未压缩明文，test.sh 现场 gzip 生成 .gz（解压内容一致，断言不受影响） |

## 源码修改
无（patches_applied=[]，未修改上游任何源码与测试）。

## 依赖版本
- zlib/1.3.1.1（制品仓 ohpcd 已发布）

## 验证结果
```bash
# macOS 原生辅助验证（非真机证据）
tests/run-tests.sh        → passed all 5 tests
test_package/test.sh      → U1-U5 5/5 PASS + H1 e2e PASS（contigs=6319）
# OHOS 交叉编译（ohos-local profile）
conan create → conan-verify G0-G4/L2/L4/L5 全过（can_run=False，run 阶段跳过）
# 远程 HarmonyOS CI（真机终态证据）
CI #66602（worker OpenHarmonyPCDeveloper-CI-033，commit c2329ef6）全绿：
build() 内 bash run-tests.sh 上游 5/5 通过；test_package U1-U5 重放 + H1
鸿蒙 e2e 通过；L0/L1 门禁通过。注：build() 上游测试须 cwd=tests/（上游
脚本按 ../velveth 相对路径取二进制），首轮 CI 曾因此失败已修复。
```

## 注意事项
- fmt_auto_mode.t 在 worker 上运行期依赖外部 gunzip/pigz（autoOpen.c 的
  popenNoStderr 路径）；若 worker 无 gunzip 需后续适配（备用方案：
  autoOpen 对 .gz 回退 zlib gzopen）。
---

**编译结束**: 2026-09-30 19:59
**最终状态**: published
