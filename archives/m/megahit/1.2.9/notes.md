# megahit 1.2.9 适配笔记（收尾-1B / B 机）

## 编译环境
- 构建系统: cmake（cmake 4.1.2, clang 15.0.4 aarch64, GNU Make 4.4.1, OpenMP libomp）
- 编译日期: 2026-09-28
- 编译器: /data/service/hnp/bin/clang（OHOS SDK llvm 15）
- 状态: built
- 依赖: zlib/1.3.1（ohpcd 制品仓, 仅静态 libz.a）; OpenMP 由 clang -fopenmp=libomp 提供
- 语言预检: cpp（cmake; 源文件 44: cpp 41 / c 2 / py 1, 主体 93%）

## 编译步骤

```bash
# conan 流程（与 conan-verify 等价）:
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

探索构建（.work 手工路径，用于补丁定型与上游测试实测）:

```bash
cmake -S $W -B $W/build -DCMAKE_BUILD_TYPE=Release -DZLIB_ROOT=<full_deploy zlib prefix>
cmake --build $W/build -j2   # 三个 megahit_core* 全部链接成功
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Could NOT find ZLIB`（cmake configure 失败） | OHOS 无系统 zlib 开发文件 | conan requires zlib/1.3.1；recipe 用 ZLIB_INCLUDE_DIR/ZLIB_LIBRARY 直指制品（依赖仅静态 libz.a） |
| 2 | cmake 4.1.2 拒绝 `cmake_minimum_required(2.8)` | CMake >= 4 移除 <3.5 兼容 | 补丁 0001: min version -> 3.5 |
| 3 | aarch64 无 `x86intrin.h`/`cpuid`，`-mbmi2`/`-mpopcnt` 旗标不识别 | 上游 x86 内联/内建无架构守卫（E093/E493/E513 族） | 补丁 0002/0003/0004：守卫 + 可移植 pdep 软件回退 + 旗标按 CMAKE_SYSTEM_PROCESSOR 门控（等价上游 master PR #368） |
| 4 | 包装脚本 `env: exec python: No such file or directory` | OHOS 无裸 `python` 命令 | 补丁 0003: shebang -> python3 |
| 5 | `os.mkfifo` → PermissionError(EPERM)，全部 --test 用例起跑即挂 | HMDFS 不支持命名管道 | 补丁 0003: try/except 降级为普通临时文件（先解压完再喂 buildlib），运行时能力探测、无平台宏 |
| 6 | ★ 上游缺陷：≥3 线程组装 SIGSEGV（本机 20 线程默认必崩） | aarch64 弱内存序暴露 megahit sdbg 并发写缺陷（x86 TSO 掩盖；证据见下「上游线程缺陷取证」） | 未修（上游并发 bug，超出配方范围）；notes/知识草稿留档，测试统一 -t 2 |

## 上游线程缺陷取证（问题 #6）

- 现象：`megahit -r random.fa --k-list 255`（上游 simple_test 第 4 例，默认线程=cpu_count=20）Exit code -11（SIGSEGV）；`--test -t 4`（第 2 例）同崩；`-t 3/4/8/20` 全崩，`-t 1/2` 稳定通过。
- ASan（-fsanitize=address,undefined 重建后复现）：
  `heap-buffer-overflow WRITE of size 64` at `BufferedReader::read` (utils/buffered_reader.h:34)
  <- `LoadSdbgRawContent` (sdbg/sdbg_raw_content.cpp:83) <- `SDBG::LoadFromFile` (sdbg/sdbg.h:27)
  tip_lables 分配 1981×64B（=meta words_per_tip_label×tip_count），实际写入 ≥1982 条 tip label。
- 数据面对账：.sdbg_info 桶记录与 .sdbg.N 数据文件不一致（桶 3167 声称在 file4 offset 30668，file4 实际仅 28470B；meta tip 总数 1981 = 分配量，数据流 tip 位更多）→ 构建阶段并发写 sdbg 时元数据/数据撕裂。
- 判别实验：输出/临时目录放 tmpfs（/data/storage/el2, 16G RAM 盘）仍复现 → 排除 HMDFS 文件系统因素；-t 1 单线程稳定通过 → 排除确定性逻辑 bug；x86 上游 CI 常年绿（TSO 强内存序掩盖）。结论：aarch64 弱内存序暴露的上游并发缺陷。
- ptrace 被设备安全策略禁用（gdb/lldb 均不可用），未继续逐行定位上游同步缺失点。
- 上游 master（v1.2.9 之后）无相关修复（PR #368 仅架构编译适配）。

## 上游测试（R51 实测，CMakeLists `simple_test` 9 例）

五维数：上游用例总数 9 ｜ 执行 9 ｜ 通过 7 ｜ 失败 2 ｜ 跳过 0
（另有 test_package/test_megahit.py 消费者断言 5 组：dumpversion=1.2.9、组装退出 0、final.contigs.fa 非空、fastg 产物非空、readstat 退出 0；conanfile.py test() 驱动）

| 例 | 命令 | 结果 |
|----|------|------|
| 1 | `./megahit --test -t 2` | PASS |
| 2 | `MEGAHIT_NUM_MERCY_FACTOR=1.5 ./megahit --test -t 4 --mem-flag 0 --no-hw-accel` | FAIL(rc=-11, 上游线程缺陷) |
| 3 | `./megahit --test -t 2 --kmin-1pass --prune-level 3 --prune-depth 0` | PASS |
| 4 | `./megahit -r random.fa --k-list 255 --min-count 1 -o test-random` | FAIL(rc=-11, 上游线程缺陷, 默认 20 线程) |
| 5 | `./megahit --test -t 2 --mem-flag 2 --keep-tmp-files -o test-fastg` | PASS |
| 6 | `./megahit -r test_data/empty.fa -o test-empty` | PASS |
| 7 | `./megahit -r test_data/r4.fa -o test-no-contig` | PASS |
| 8 | `./megahit_toolkit contig2fastg 59 ...` | PASS |
| 9 | `./megahit_toolkit readstat < ...` | PASS |

补充（同一缺陷的额外佐证，非上游用例）：默认 k-list 全基因组随机组装在 -t 1/-t 2 通过（1000 contigs 输出），-t 3 起崩。
两处失败同根因（上游并发缺陷），均为"上游测试在本平台按原文运行"的如实回填；-t ≤2 时 megahit 功能完整正确。

## 源码修改（patches/，refresh-patch --auto 生成）

- 0001-CMakeLists.txt.patch：min version 3.5；x86 旗标按处理器族门控
- 0002-src-kmlib-kmrns.h.patch：x86intrin.h/Pdep 守卫 + 软件回退
- 0003-src-megahit.patch：shebang python3 + mkfifo 降级（运行时探测）
- 0004-src-utils-cpu_dispatch.h.patch：cpuid 守卫，非 x86 返回 false
- 无平台宏（PF5 合规）；无生成文件改动

## 知识库检索结论（供 B 判定）

- `recipe-search megahit`：6173 条语料无相似配方（无同族归并对象）
- 命中机制（本次新适配点，建议 create）：
  - HMDFS 命名管道 EPERM → 包装层 try/except 运行时探测降级（新机制）
  - 上游并发缺陷在 aarch64 弱内存序暴露（ASan + 数据面对账 + tmpfs 判别的新取证模式）
- 归族对照：x86 内联守卫走既有 E093/E493/E513 族思路（本次补丁与上游 PR #368 等价，不另立新条目）

## 依赖版本

- zlib/1.3.1（ohpcd, 静态）; conan 2.29.1(OHOS 版); cmake 4.1.2; clang 15.0.4; python3 3.12+（运行时包装脚本）

## 验证结果

```bash
$ ldd-build: 3 个 megahit_core* 链接成功（-fopenmp=libomp, -static-libz）
$ ./megahit_core dumpversion  → 1.2.9
$ conan-verify megahit 1.2.9  → 见 reports/（G0-G3 判决行）
$ finish megahit 1.2.9 built  → 见 .ci-result.json
```

## 注意事项

- ★ 本平台使用 megahit 组装请显式 `-t 2`（或 ≤2）；默认线程数（cpu_count）会触发上游并发缺陷 SIGSEGV。修上游前不要放宽。
- CI 无需 python 之外的解释器；megahit 包装脚本为 python3。
- recipe build 固定 `-j2`（OpenMP 编译单元内存大户，19 物理核机器上 -j2 峰值 RSS 实测 <2GB）。
---

**编译结束**: 2026-09-28 05:26
**最终状态**: built
