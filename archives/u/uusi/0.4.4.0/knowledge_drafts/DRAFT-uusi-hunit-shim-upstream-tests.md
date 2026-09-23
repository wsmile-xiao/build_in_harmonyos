# uusi 0.4.4.0 知识草稿：用最小 HUnit 兼容层实跑上游测试

## 适用范围
只适用于 `uusi` 0.4.4.0 这种上游测试存在、但测试框架依赖很薄的 Haskell/Cabal 包。

## 现象
上游 `uusi.cabal` 声明了 `test-suite uusi-tests`，测试入口是 `test/Main.hs`，但额外依赖 `HUnit`。
按 PR 审查规则，上游测试存在时必须尽量实跑，不能简单全量跳过。

## 结论
本轮没有把完整 HUnit 作为依赖混入 `uusi` PR，而是在源码测试目录补一个 package-local 的 `Test.HUnit` 模块。
这个模块只实现上游测试实际用到的 5 个接口：
- `Test`
- `test`
- `(~:)`
- `(~=?)`
- `runTestTTAndExit`

这样 `test/Main.hs` 的断言逻辑保持不变，`Setup configure --enable-tests` 和 `Setup test --show-details=direct` 能真实执行上游 5 个测试用例。

## 证据
上游测试覆盖：
- remove all version constraints
- overwrite
- remove
- replace
- replace and remove

这些用例只需要相等性断言和失败退出语义，不依赖 HUnit 的 fixture、计数器、断言组合器或格式化输出细节。

## 复用边界
这个办法只能用于测试框架 API 使用面极小、且兼容层不会改变被测业务逻辑的包。
如果上游测试使用 HUnit 的复杂断言、TestList/TestLabel 结构检查、fixture、异常断言或 test-framework 集成，应先拆出 HUnit 依赖库单独适配，而不是在业务包里继续扩大兼容层。
