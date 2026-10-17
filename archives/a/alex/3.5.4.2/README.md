# alex 3.5.4.2 — HarmonyOS PC 适配

alex 是 Haskell 词法分析器生成器（上游 https://hackage.haskell.org/package/alex，BSD-3-Clause）。

## 构建
- 工具链：GHC 9.14.1（harmonybrew `brew install ghc`）
- `runghc Setup.hs configure --prefix=/usr --enable-executable-static`（静态链接，避免动态库缺失）
- `runghc Setup.hs build`；package() 直接复制**未剥符号**的 dist 二进制（`Setup.hs copy` 剥离符号会导致 OHOS 无法执行）

## 使用
- 运行时模板（AlexTemplate.hs/AlexWrappers.hs）随包安装于 `share/alex-3.5.4.2/`；alex 默认按编译期烤入的绝对 datadir 查找，调用时需 `--template=<包目录>/share/alex-3.5.4.2`
- 注意：alex `--help` 在 OHOS 上 GHC RTS 间歇性挂死（平台怪癖，非本适配引入）

详见 archives/a/alex/3.5.4.2/ 的 conanfile.py、manifest.yaml、test_package/。
