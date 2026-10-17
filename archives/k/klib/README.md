# klib

klib 是 attractivechaos 维护的轻量级通用 C 组件集合，提供哈希表、B-tree、AVL tree、排序、动态数组、字符串、序列解析等实现。

## OHOS 适配

- 固定无正式 Release 的上游快照提交，保证源码可复现。
- 保持上游“复制头文件或 C 源文件使用”的组件化发布方式。
- 使用 Conan OHOS profile 编译 19 个上游测试目标并运行功能测试。
- 提供真实消费者集成测试验证安装后的 `khash` 与 `kstring` API。

## 依赖

- zlib（kseq/bgzf 相关组件）

## 参考

- https://github.com/attractivechaos/klib
- https://attractivechaos.github.io/klib/
