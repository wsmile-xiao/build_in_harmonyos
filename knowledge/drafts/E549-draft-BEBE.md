# E549 — 生成器-运行时分离包的消费者测试：在线生成器不可用时的手写生成代码等价物

> Status: DRAFT | 实例: libantlr3c 3.5.3（HarmonyOS PC 构建 OHOS AArch64）
> severity 🟡 2 | category: ohos, cross-compile, conan, testing, api

## 错误特征

```
# test_package 若试图依赖在线生成器（错误方向 A）：
ERROR: Unable to find package 'jdk'/'openjdk' in remotes
ClassNotFoundError / 'java' not found (目标环境 OHOS AArch64 无 JVM)

# test_package 若因此跳过消费者验证（错误方向 B，静默缺失）：
test_package: SKIP (no generator available)
# → 包的公共 API 完全没有消费者级验证，CI 假绿
```

## 触发条件

- 构建系统: 任意（本例 autotools）
- 阶段: testing（test_package / 消费者验证）
- 形态: 上游是"**生成器 + 运行库**"分离发布的语言工具链——宿主端生成器（如
  ANTLR Java Tool：grammar→C 源码）与目标端运行库（如 libantlr3c：驱动生成的
  lexer/parser 源码）是两件独立制品。制品仓只收录**目标运行库包**，生成器
  不在包依赖图中；目标环境（OHOS AArch64）通常无 JVM。此时 test_package
  如何验证运行库的完整公共面（字符流、token 流、识别、语法错误、资源释放）？

## 根因分析

以 ANTLR 为例：`libantlr3c` 是运行库——**它自己不解析 grammar**，只提供驱动
"生成代码"的 C API（流、token、识别器、树、调试等）。真正的识别逻辑来自
ANTLR Java 工具从 `.g` 文件生成的 C 源码。因此：

- **宿主/目标边界**：Java 工具是宿主端开发期工具（与 bison/flex 同类），
  属于 `tool_requires` 域；libantlr3c 是目标端运行库，属于 `requires` 域。
- **包边界**：制品仓无 ANTLR Java 生成器包，也**不应该**为了测试而新增
  java/jdk 依赖（违反仓库先例：不新增制品仓不存在的依赖）。
- **验证缺口**：上游 runtime 源码树零测试零示例（审计结果 0/0/0/0），
  若 test_package 只做"链接成功"级别的验证，字符流/token 流/识别/错误/
  释放五类公共 API 全部无消费者级证据。

## 解决方案

### 推荐方案：手写生成代码等价物

在 test_package 中手写"生成器本应生成的代码的等价物"——不调用生成器、
不新增依赖，按上游生成代码的结构与 API 契约编写最小 lexer/parser C 源
（等价于对 grammar 的最简识别机实现），使消费者测试覆盖运行库真实公共面：

1. **字符流**：`antlr3FileStreamNew(path, ANTLR3_ENC_8BIT)` 构造输入流；
2. **Token 流**：`antlr3CommonTokenStreamNew(lexer->rec->state->tokenStream)`
   构造 token 流；
3. **识别成功**：喂入合法输入，断言 token 数、类型、文本、行号；
4. **语法错误**：喂入含错误输入，断言 `reportError` 回调触发与恢复；
5. **资源释放**：`->free(...)` 全链释放，断言返回值（见下方 3.5.3 API 语义注）。

结构参照（可选，宿主侧）：若需确认"生成代码长什么样"，在宿主用生成器
产出参照物（`java -cp antlr-3.5.3-complete.jar org.antlr.Tool Tiny.g`），
或对照上游源码树自带的生成代码样本。**参照物只在宿主生成，绝不进入
目标测试执行链**。

### 回退方案：上游自带样本

若上游发布物自带可独立编译的生成代码样本（ANTLR 官方示例包等），直接
以该生成物为消费者测试载体。libantlr3c 上游 runtime/C 无自带示例，故
本例用推荐方案。

### 禁止（安全边界）

- ❌ 给运行库包 `requires`/`tool_requires` 新增 java/jdk——目标产物引入
  制品仓不存在的依赖；
- ❌ "无生成器则跳过测试"——消费者验证静默缺失（no-silent-skip）；
- ❌ 在目标环境 exec java -jar——伪造"目标端可跑生成器"假象，目标无 JVM
  时挂死，即便宿主能跑也验证的不是目标能力；
- ❌ 只做链接级验证——五类公共 API 无消费者级证据。

## libantlr3c 3.5.3 API 语义注（消费者测试编写要点）

3.5.3 版本的具体语义（均经真机验证，勿凭记忆写错）：

- `index()`/`seek()` 是**绝对指针**语义（`seek(n)` 到绝对索引 n，非相对）；
- `mark()` 返回 markDepth（当前标记深度），非其他语义;
- token 流取 token 用方法 `_LT`（`ts->_LT(ts, i)`），`LT` 是字段非方法；
- `consume` 在 istream（`is->istream->consume(is->istream)`），非直接在流上;
- 8 位编码用宏 `ANTLR3_ENC_8BIT`（非字符串）；
- 不要覆盖 `rec->super`（exConstruct 强转导致结构错位段错误），用户上下文
  挂 `lexer->ctx`；
- `--enable-64bit` 必需（否则 ANTLR3_MARKER 为 INT32，AArch64 LP64 下指针
  截断）。

## 验证方式（输出）

1. `conan create . -pr:h=<ohos> -pr:b=<ohos>` 成功，包内 `lib/libantlr3c.so`
   ELF64 AArch64；
2. `conan test test_package/ libantlr3c/3.5.3@ ...`：test_package 手写
   consumer_tests.c 编译链接运行，`1/1 Test #1: consumer_tests Passed`；
   测试覆盖上述五类公共 API（精确断言计数见 test_package/MANIFEST.yml）；
3. `readelf -h lib/libantlr3c.so`：ELF64 / AArch64 / 动态库；
4. 测试二进制 ldd 无 JVM/libjava 依赖——证明生成器未参与目标测试链。

## 与已有知识的差异（查重）

- **E546**（libmagic 构建期生成器选择）：处理**构建期**"工具编译数据→库
  消费数据"两阶段构建的生成器选择（同 ABI 复用 target 工具 vs 两阶段
  host tool）；E549 处理**测试期**消费者验证在生成器不可依赖时如何不造假、
  不跳过、不越依赖边界。构建期生成器选择在 libantlr3c 根本不出现（上游
  构建不用生成器），两者边界正交。
- **E456**（Qt host moc/rcc/uic 分离）：目标包与宿主工具**目录/前缀**分离，
  仍是构建期问题；E549 是测试期消费者验证方法。
- **E359**（cmus HOSTCC/HOSTLD 映射）：上游有 host 编译变量待映射；本条目
  上游无 host 变量，问题不在构建配置。
- **E374**（签名工具缺失时 NOT_RUN）：处理"能力缺失时如何诚实报告"；
  E549 的场景根本不该把生成器引入目标测试链，无需 NOT_RUN 语义。
- **E423**（交叉 Binutils 身份闭环）：同包内宿主工具与目标产物的**身份
  分类与验证**；E549 是跨包的生成器/运行库分离 + 测试期方法。
- **E243**（协议数据包逐文档生成器测试）：数据包消费者测试要用**真实
  生成器注册 API**；E549 相反——生成器不可依赖，用手写等价物替代。
- **E298/E307/E239 等**：test_package 的运行环境、编译方式、诊断保留等
  一般方法论，不涉及生成器/运行库分离场景。

## 可复用于哪类项目

- **ANTLR 系**（本例 libantlr3c 3.5.3；未来 antlr4-c3runtime 等）；
- **protoc + protobuf-c**：生成器宿主、运行库目标；
- **wayland-scanner + libwayland**：协议生成与运行库分离；
- **glib-mkenums/glib-genmarshal + glib**：模板生成器与运行库；
- **bison/flex 生成代码 + liby/libfl**：同构的生成器/运行时分离；
- 任何"代码生成器是宿主工具、运行库是目标产物"的 Conan 包，且制品仓
  无生成器包时的消费者测试设计。

## 关联条目

- 相关: E546, E456, E359, E374, E423, E243
- 原则: no-silent-skip, provenance-verifiable
