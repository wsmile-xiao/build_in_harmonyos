# uusi 0.4.4.0 知识草稿：Conan 2 下清理 os.version

## 适用范围
只适用于本包的 Conan 2 recipe 和 test_package。

## 现象
OHOS 配置下，`os.version` 对这个 Haskell 小工具并没有实际参与构建决策。
如果不清理，Conan 2 可能把它当成无效或不必要的系统设置，干扰 `conan create` 和 `test_package` 的一致性。

## 结论
在 `conanfile.py` 和 `test_package/conanfile.py` 里都加：
`self.settings.rm_safe("os.version")`
就够了。

## 证据
本轮已经在 recipe 和 test_package 两边都加入该处理，随后 `conan create` 与 test_package 通过。

## 复用边界
这不是“所有 OHOS 包都必须删 os.version”的通则。
它只适用于本包这种不依赖 `os.version` 分支的场景。
