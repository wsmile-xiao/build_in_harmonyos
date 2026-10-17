# uusi 0.4.4.0 知识草稿：Setup.hs 两段式引导

## 适用范围
只适用于 `uusi/0.4.4.0` 这次 HarmonyOS 真机适配，不外推到其他 Haskell 包。

## 现象
上游源码包是 Cabal `build-type: Simple`，但真正参与构建的是随源码带的 `Setup.hs`。
如果直接把它当成普通库包去配，后续 `configure` / `build` 会缺少 `Setup` 这个中间产物。

## 结论
真机验证时必须先执行：
`ghc --make Setup.hs -o Setup`
然后再执行 `./Setup configure ...` 和 `./Setup build`。

## 证据
本轮真机 `conan create` 已跑通上述流程，`Setup.hs`、`Setup configure`、`Setup build` 都成功。

## 复用边界
这个草稿只说明“源码包自带 Setup.hs 的 Cabal Simple 项目”在 OHOS 上的引导顺序。
它不代表所有 Haskell 包都需要手工编译 `Setup.hs`。
