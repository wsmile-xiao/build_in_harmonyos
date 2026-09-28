# uc-echo 1.12 适配笔记

## 软件背景
- ECHO：短读长测序（Illumina）数据的无参考纠错工具，贝叶斯最大后验校正（Genome Research 2011）。
- 上游主页 http://uc-echo.sourceforge.net/ ；构建系统：裸 Makefile（无 configure）；产物：6 个 C++ 命令行工具
  （hashing/HashMerge/NeighborJoin/NeighborJoinParam/NeighborMerge/Voting）+ Python2 驱动 ErrorCorrection.py。
- 零外部 C/C++ 依赖（W0 preflight 通过）；许可 BSD-2-Clause；上游停更（2012，v1.12 终版）。

## 货源核验（官方原件，非池址例外）
- 官方托管：SourceForge（debian/watch：`https://sf.net/uc-echo/echo_v([\d_]+)\.tgz`；copyright Source: 官方主页）。
- 直链 `downloads.sourceforge.net/project/uc-echo/echo_v1_12.tgz` 404（真实路径在 `source release/` 子目录），
  规范官方 URL `https://sourceforge.net/projects/uc-echo/files/echo_v1_12.tgz/download` 可达（HTTP 200，重定向至 master.dl）。
- 采样：官方 /download URL ×3、downloads.sourceforge.net source release 直链 ×3，均 461450 字节、
  sha256=b83c8b8acfd285ae1433b0cb3f2a88d968e0f2135cc6d6e466e5718a0fe95255，与 Debian 池 uc-echo_1.12.orig.tar.gz
  给定 sha256 全等——Debian 未重打包，字节同一。conandata.yml 采用官方 URL + 该 sha256，无需例外口径。

## 编译环境
- 构建系统: makefile（无 configure，R9 用 -j1；R33 编译器取 Conan conf）
- 编译日期: 2026-09-27
- 编译器: OHOS SDK native clang/clang++ 15.0.4
- 状态: built

## 编译步骤
- 探索：`make CXX=clang++ CXXFLAGS="-Wall -O3 -m64 -fsigned-char"`（经 gate.sh --light + build-slot.sh --kind short 过闸）。
- 配方：`conan create`（conan-verify G2），build() 为 `make CXX=<conf cpp> CXXFLAGS="-Wall -O3 -m64 -fsigned-char" -j1`。
- Makefile 无 install 目标（无 E108 ginstall 风险），package() 直接拷 6 个二进制到 bin/。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'tr1/unordered_map' file not found`（首错） | OHOS clang/libc++ 不带 C++ TR1 头；源码为 2011 年 C++03/TR1 风格 | 10 个文件 TR1→C++11 std 现代化：`std::tr1::X`→`std::X`、`tr1::X`→`std::X`、`<tr1/y>`→`<y>`（0001-0004/0006-0011 号补丁） |
| 2 | `error: use of undeclared identifier 'close'`（MMAP.hpp:37） | glibc 经其它头传递声明 close，OHOS libc 不传递 | MMAP.hpp 显式 `#include <unistd.h>`（0005 号补丁） |
| 3 | `index_t`（=plain char）存 -1（`nerr=-1`、`assert(nerr!=-1)`）在 aarch64 静默失真 | aarch64 plain char 默认无符号；上游按 x86 有符号 char 语义编写 | 编译加 `-fsigned-char` 恢复 x86 语义（配方 CXXFLAGS，非源码补丁） |
| 4 | K0：`--version`/`--help` rc=134（直落主逻辑，MMAP 抛异常 abort） | 手写 argv 解析器无 --version/--help 分支 | util.hpp Options 构造器前置真实现：打印版本/用法后 exit(0)（0012 号补丁，全 6 二进制共享生效） |
| 5 | make 高负载瞬态失败一次（HashMerge，load 22+，PSI avg10≈57%） | 设备高负载瞬态；同命令手动复跑成功 | 复跑通过；conan-verify 干净重建为准 |

## 源码修改（patches/，refresh-patch --auto 生成，12 个）
- 0001-0004、0006-0011：TR1→std 现代化（纯语义等价替换，无逻辑变更；`Kmer_hash`/`Kmer_cmp` 与 std::unordered_map
  四参模板兼容已核实——Kmer_cmp 是等值谓词、Kmer_hash 返回预计算哈希）。
- 0005：MMAP.hpp 增 `#include <unistd.h>`。
- 0012：util.hpp Options 增 `--version`（输出 `uc-echo (ECHO) 1.12`）与 `--help`（真实选项清单）处理，exit 0。
- 全部补丁零平台宏（无 `__OHOS__`）；-fsigned-char 走配方 CXXFLAGS 不进补丁。

## K0 实测证据
- 补丁前：`./hashing --version` rc=134（libc++abi 未捕获异常 abort）、`./hashing --help` rc=134。
- 补丁后：6/6 二进制 `--version` rc=0 且 `--help` rc=0；`./hashing --version` 输出 `uc-echo (ECHO) 1.12`。

## 上游测试三步法（R51）
1) 清点：无 tests/ 目录；Makefile 仅 all/clean/release（无 test/check 目标）；无 ctest/pytest 注册；
   自带 sample_data.txt + sample_answer.txt（各 10000 行）为示例数据。
2) 实际运行：示例流程需 Python2 + SciPy/NumPy 驱动（ErrorCorrection.py 第 16-20 行 scipy/numpy 导入、
   第 110 行 `print stdout` 为 Python2 语法）；CI 能力矩阵无 Python2/SciPy → 不可运行（具体技术原因）。
   且 README 明言纠错输出与 sample_answer.txt "There will be differences"——非逐字断言、非自动测试。
3) 申报：上游确无自动化测试（证据见 test_package/MANIFEST.yml）；以消费者端到端测试替代——
   构造 12 条目输入（6 reads + 反向互补，2 处注入测序错误），串全 6 个二进制
   （hashing×2 → HashMerge → NeighborJoin×2 按 kmer 区间 → NeighborMerge → Voting；NJParam 以模型选择路径 rc 覆盖），
   纠错输出金标逐字 cmp（两个错误读均被纠回一致序列）+ 两次运行字节级确定性验证（DETERMINISM_PASS）。
   金标 sha256=1a1bc2bd60c8072a88e246e0865d25758d2f267cd6a611ca6b18bb11a028a328。

## 依赖版本
- 无外部依赖（零 requires）。

## 验证结果
```bash
# 探索性构建（gate+slot 过闸）：6/6 二进制建成
make CXX=clang++ CXXFLAGS="-Wall -O3 -m64 -fsigned-char"  # rc=0
# K0（补丁后）：6/6 version_rc=0 help_rc=0
# 消费者流水线：DETERMINISM_PASS + SEMANTIC_PASS（错误读纠回一致序列）
# conan-verify：见 reports/ 与 .ci-result.json
```

## 交付物
| 文件 | 说明 |
|------|------|
| bin/hashing、HashMerge、NeighborJoin、NeighborJoinParam、NeighborMerge、Voting | 6 个命令行工具（application 包） |

## B 判定（终判：create）
- 首错机制「OHOS clang/libc++ 无 TR1 头 → pre-C++11 源码 tr1→std C++11 现代化」：
  知识图谱 index.tsv/E*.kv 零 tr1 同层条目（grep 实证），且该机制可跨库复用（任何 pre-C++11
  C++ 源码在 OHOS 上同理命中）→ 升 create。
- 交付物：knowledge/drafts/DRAFT-uc-echo-1.12-tr1-std-cpp11-modernization.{kv,md} 成对落本 PR。
- Issue：`【知识库扩展】uc-echo 1.12：OHOS libc++ 无 TR1 头，pre-C++11 源码 tr1→std 现代化`——由主理窗创建回填（子代理无平台写权限）。
- 次级机制「aarch64 plain char 无符号需 -fsigned-char」未单独立条，已写入 notes 与 manifest knowledge_gained（同 PR 可复核）。

## 注意事项
- `-fsigned-char` 必须保留：去掉后 aarch64 上 `nerr=-1` 变 255，邻接过滤 `1.0*nerr/overlap>e` 会静默错误拒绝邻居，改变纠错行为（编译不报错）。
- NeighborJoin 有 `assert(st1<=st2 && ed1<=ed2)`：上游分块路径（DataBlockSize<nData）本身会触发断言，驱动注释明言
  "DataBlockSize should be nData (the entire data set)"——实际仅支持单块 NJ，测试与使用均走单块路径。
- /tmp 只读（E002），一律用 $TMPDIR。

- 编译结束: 2026-09-27 03:00（finish W3 本地 CI 全绿 1/1，.ci-result.json exit_code=0）
- 最终状态: built
