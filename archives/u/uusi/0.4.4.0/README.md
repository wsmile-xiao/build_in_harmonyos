# uusi 0.4.4.0 - HarmonyOS 前置适配

uusi 是一个用于语义化改写 `.cabal` 文件的小工具，上游仓库：
https://github.com/berberman/uusi

## 进度
- 构建系统：Haskell / Cabal `build-type: Simple`
- 源码包：Hackage `uusi-0.4.4.0.tar.gz`
- 本机状态：已完成源码、cabal、CLI 分析，并在真机跑通 `conan create` / `test_package`
- 知识草稿：已补 6 份包内草稿，覆盖 Setup.hs 引导、GHC libdir、PATH、os.version、test_package 契约和 HUnit 测试兼容层
- issue：无需处理

## 适配思路
- 使用 `ghc --make Setup.hs -o Setup`
- 再执行 `Setup configure --prefix=/usr --enable-executable-static --enable-tests`
- 构建后执行 `Setup test --show-details=direct`，实跑上游 `uusi-tests`
- 打包三个可执行文件：`uusi`、`gen-setup`、`uusi-extract`
- 上游测试只用 HUnit 的极小断言 API；本轮通过包内测试补丁提供等价 `Test.HUnit` 模块，不把独立 HUnit 适配混入 `uusi` PR

## 下一步
- 整理本轮适配结论与交接说明
