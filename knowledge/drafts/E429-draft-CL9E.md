# E429 — header-only C++03 短名宏展开引用非限定符号；成功静默的测试运行器需要显式 pass 标志取证

## 错误特征
```text
error: use of undeclared identifier 'the_log'; did you mean 'clue::the_log'?
note: expanded from macro 'LOG_INFO' / 'LOG_ERROR'
```
或反向：测试二进制 exit 0 但 stdout 为空，拿不到任何用例数/断言数证据
（本版本 lest_cpp03 的成功摘要受 `failures>0 || output.pass()` 门控）。

## 触发条件
- 构建系统: make / cmake / conan（test_package 消费者编译）
- 阶段: compilation（test_package）、testing（取证运行）

## 根因分析
clue 一类的 C++03 header-only 库把短名宏（`LOG_INFO` 等）展开为对
`the_log()` 的**非限定**调用；上游测试 TU 能编过是因为其 preamble 里有
`using namespace clue;`。消费者若写成 `clue::LOG_INFO(x)` 也不合法——
宏在限定符之后才展开，`clue::` 前缀直接破坏语法。
另外，2015 年前的 lest_cpp03 成功路径默认静默：`./test_clue` exit 0 且
零输出，无法为 MANIFEST.yml / PR 正文提供可核对的用例计数。

## 解决方案

### 推荐方案
test_package 源文件复刻上游测试 TU 的 preamble 惯例（`using namespace <lib>;`），
不要限定宏调用；上游 Makefile 调用保留为阻塞门禁（失败必打印、非零退出），
数字取证单独跑一次带 pass 标志的调用（clue/lest_cpp03：`./test_clue -p`，
输出 `All 15 selected tests passed.` 与逐条 `passed:` 行）。

### 禁止做法
- ❌ `clue::LOG_INFO(...)`：宏名不是命名空间成员，限定写法破坏预处理。
- ❌ 把"静默 exit 0"当测试证据写进 MANIFEST/PR：拿不出用例数，评审即拒。

## 验证
```bash
make -j2 -C tests                      # 阻塞门禁：编译+运行（成功静默）
(cd tests && ./test_clue -p)           # 取证：15 selected / 25 断言评估
conan create ... && conan test ...     # 消费者 14/14 CHECK
```

## 关联
- 触发软件: clue 1.0.0（archives/c/clue/1.0.0，feat/clue-1.0.0）
- 相关条目: E321（martinmoene lite 系 Conan2 header-only 配方骨架）、
  E257（无构建系统 header-only 的 G1 显式 build() 要求）
- 本条目互补点: E321/E257 覆盖配方结构；本条覆盖**宏可见性 + 取证静默性**
  两个上游测试/consumer 层面的坑。
