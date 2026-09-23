# uusi 0.4.4.0 知识草稿：GHC 需要看见 OHOS 工具链

## 适用范围
只适用于本轮真机上的 GHC 交叉/原生混合验证。

## 现象
`Setup build` 不是纯 Haskell 编译。
它会继续调 `clang`、`ld.lld`、`ar`、`ranlib`，如果 PATH 没有把 OHOS 工具链放到前面，GHC 会在外部工具查找阶段失败。

## 结论
成功组合里，PATH 需要把 `/data/service/hnp/bin` 放在前列，再接 `tmp/codex-bin` 和用户常规工具目录。
这样 GHC 既能找到外部编译器，也能继续调用自己复制出来的 `ghc` / `ghc-pkg`。

## 证据
本轮真机成功运行时使用的 PATH 前缀就是：
`/data/service/hnp/bin:/storage/Users/currentUser/tmp/codex-bin:/storage/Users/currentUser/usr/local/bin`

## 复用边界
这个结论只约束“GHC 通过 Setup.hs 驱动 OHOS 本地工具链”的场景。
不代表所有 Conan recipe 都需要把 `/data/service/hnp/bin` 放到 PATH 前列。
