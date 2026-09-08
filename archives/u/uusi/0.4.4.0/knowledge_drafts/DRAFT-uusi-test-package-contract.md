# uusi 0.4.4.0 知识草稿：test_package 要测三条入口

## 适用范围
只适用于 `uusi` 这个命令行小工具的 Conan test_package 设计。

## 现象
对 CLI 工具来说，只检查二进制是否存在太弱了。
如果不调用真实命令，很容易把“能打包”误当成“能用”。

## 结论
`test_package` 至少要覆盖三件事：
- `uusi-extract` 的元信息读取
- `uusi` 的语义改写
- `gen-setup` 的 `Setup.hs` 生成

同时还要确认三个可执行文件都被打进包里。

## 证据
本轮真机验证已经通过这几条断言：
- `uusi-extract --print-name -> sample`
- `uusi-extract --print-version -> 1.2.3.4`
- `uusi -dsemigroup removed semigroup`
- `uusi default --all removed version constraints`
- `gen-setup wrote Setup.hs`

## 复用边界
这个草稿只说明 `uusi` 的最小可用契约。
别的 CLI 包可以借鉴“入口覆盖 + 语义断言”的思路，但断言内容要按各自命令重写。
