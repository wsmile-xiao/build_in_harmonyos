# mptp

多速率 Poisson tree processes 物种界定命令行工具，支持 rooted/unrooted
Newick 输入、最大似然、MCMC 和 SVG 输出。上游为
https://github.com/Pas-Kapli/mptp ，许可证 AGPL-3.0-or-later。

0.2.5 适配使用官方发行包完整的 22 个生产 C 文件及配对 parser/lexer，
以 Conan/CMake 原生构建，不修改分析算法。运行时只需系统 libc/libm。
生成物缺失或 grammar 改动时不能沿用本版不依赖 Flex/Bison 的结论。

当前尚未发布；包内 `bin/mptp` 由 Conan run environment 提供。
