# E10968 — 用具体 traits 后端实例化模板化浮点算法

## 可复用场景

某些 C++ 数值库只提供以 traits/backend 类型为参数的模板算法。能 include 公共头文件、或能把一个空 consumer 编译通过，并不能证明这些算法可以与实际后端一起实例化和运行。SymFPU 的 2019-05-17 源码快照包含 core 与 utils 模板，却没有 baseTypes 后端、构建系统或上游测试套件。

## 本次适配确认的做法

1. 将 SymFPU 2019 快照的 core/utils 头文件作为唯一 Conan 包内容，声明 header-library 和空 package ID，不制造不存在的二进制库。
2. 在 test_package 放入仅供验证的具体位向量后端实现。它采用同一官方仓库后续提交 40bdec00 的 simpleExecutable traits 作为测试支持；该后端不会复制到 package/include，也不成为配方依赖。
3. 通过 CMakeDeps 找到发布包的 symfpu::symfpu target，让 test_package 同时编译后端实现与 consumer。
4. consumer 直接实例化 2019 core 的 unpack、add、multiply、pack API，以精确 IEEE-754 单精度位模式验证 5.0 的往返、1.0 + 2.0 = 3.0、2.0 × 3.0 = 6.0。
5. 对上游测试作源码审计：快照内无测试目录、测试程序、Makefile 或 CMakeLists.txt，因此上游测试总数如实记为 0；test_package 的执行只记作消费者测试。

## 边界与可迁移性

这个条目总结的是“模板算法如何在真实后端上实例化”的验证合同，不是通用的 header-only 复制配方，也不把测试后端当成产品依赖。若目标版本本身包含官方具体后端，应优先使用该版本的后端；若没有，测试辅助实现的来源、版本、改动及不进入发布包这一边界必须写清楚。

## 与现有条目的区别

- E257 记录没有构建系统时 header-only 配方仍需显式 build()。
- E307 记录无 CMake 项目的 header-only consumer 编译验证。
- E321/E322 记录通用 Conan header-only 配方和接口 target。
- E470 记录通用 header-only API consumer 验证。
- E600/E601 是 symfpu 40bdec00 版本的 x86 flags、glibc 头文件和 Makefile 问题。

这些条目均没有记录用一个具体 traits/backend 实例化 SymFPU 的核心浮点模板，并将该 backend 限定为 test_package 支持。因此本草稿只补充此缺口。