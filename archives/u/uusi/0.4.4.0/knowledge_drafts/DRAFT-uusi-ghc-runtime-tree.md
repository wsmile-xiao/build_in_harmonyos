# uusi 0.4.4.0 知识草稿：GHC 运行时目录要一并复原

## 适用范围
只适用于本轮从真机系统里拷出的 GHC 9.14.1 运行环境。

## 现象
单独复制 `ghc` / `ghc-pkg` 不够。
`ghc-pkg list` 和 `Setup configure` 都会去找默认 libdir 下的 `settings`、`package.conf.d`，还会依赖 `aarch64-linux-ghc-9.14.1-7fac` 这类运行时目录。

## 结论
把 GHC 挪到 `tmp/codex-bin` 这种可执行目录后，必须同步把：
- `/storage/Users/currentUser/tmp/lib/settings`
- `/storage/Users/currentUser/tmp/lib/package.conf.d`
- `/storage/Users/currentUser/tmp/lib/aarch64-linux-ghc-9.14.1-7fac`

恢复到同一 libdir 结构里，再执行 `ghc-pkg recache`。

## 证据
本轮真机侧在补齐上述目录后，`ghc-pkg list`、`Setup.hs` 编译和后续 `conan create` 都恢复正常。

PR CI #40535 还暴露了另一个边界：通过 harmonybrew 新安装 GHC 后，刚编译出来的 `./Setup` 本身会动态依赖 `libgmp.so.10` 和 `libffi.so.8`。因此 recipe 在运行 `Setup configure` 前，需要把 harmonybrew 下的 `gmp`、`libffi`、`ncurses` 和 GHC libdir 同时加入 `LD_LIBRARY_PATH`，并把这些目录加入 `LIBRARY_PATH` 供后续 GHC/clang 链接阶段使用。

## 复用边界
这里记录的是“复制出来的 GHC 二进制”在 OHOS 上的落地方式。
如果后续换成系统安装版 GHC，目录布局未必相同。
