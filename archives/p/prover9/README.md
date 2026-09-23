# prover9 - 一阶逻辑自动定理证明器与有限模型搜索器（LADR 工具集）

## 描述
Prover9 是一阶逻辑+等式推理的自动定理证明器（resolution/paramodulation 范式），
Mace4 是配套的有限模型搜索器（穷举小域解释找反例/模型）。两者由 William McCune
（Argonne 国家实验室，Otter 作者）开发，是自动推理领域的经典学术工具。
本包为 LADR-2017-11A 工具集全量适配，含 prover9/mace4/prooftrans/interpformat/
isofilter 等 43 个命令行工具，可用于形式化验证、逻辑教学、协议分析等场景。

## 版本信息
- 当前版本: 2017-11a（conan slug；上游发布名 2017-11A (CIIRC)，LADR-2017-11A）
- 发布日期: 2017-11（上游）；鸿蒙适配 2026-09-07
- 主页: https://github.com/ai4reason/Prover9
  （官方站 cs.unm.edu 已随原作者 2023 年去世失联；ai4reason 仓承载末代维护人
  Bob Veroff 的 LADR 延续线，R39 认定的权威镜像源）

## 编译方法
```bash
# 上游为手搓递归 Makefile（无 configure，init-build 会误判 autotools）
make all -j1 CC=clang XFLAGS="-fPIC -O2"
# 必须串行：-j2 触发 install 目标并行竞态（多子目录争抢 ../bin/）
# 附加编译标志经 XFLAGS 注入（上游 CFLAGS = $(XFLAGS) -O -Wall）
```

## 依赖
- 编译依赖: clang（profile 注入）+ make
- 运行依赖: libc
- conan 依赖: 无（零依赖纯 C）

## 功能
- prover9: 自动定理证明（给定公理+目标，输出机器可读证明）
- mace4: 有限模型搜索（小域穷举，可作定理证明的反例探测器）
- prooftrans: 证明后处理（parents_only/reformat/expand 转换）
- interpformat: interpretation 格式转换（tabular/portable 等）
- isofilter: interpretation 同构过滤
- 其余: ladr_to_tptp/tptp_to_ladr（TPTP 互转）、directproof、olfilter 等

## 已知问题
- --version 打印横幅后 exit 1（LADR 程序族惯例，测试断言只看输出内容）
- 多数二进制为 non-PIE（上游 1990s Makefile 无 -pie；L4 安全扫描仅告警）
- 源码树 bin/ 下 proof3fo.xsl 为 XSL 样式表、prover9-mace4 为 shell 包装脚本

## 安装验证
```bash
prover9 --version          # 横幅: Prover9 (64) version 2017-11A (CIIRC)
echo 'formulas(assumptions).' > t.in  # 或用上游 x2.in 群论样例
prover9 -f t.in | grep "THEOREM PROVED"
mace4 -f group2.in | grep "MODEL"     # 6 元非交换群模型
```
