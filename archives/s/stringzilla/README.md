# stringzilla

stringzilla 5.1.2 是 SIMD 加速的 C 字符串算法库。本适配提供上游 shared
core 和 `stringzilla::shared` CMake consumer target。

## HarmonyOS 适配

- 上游仓库：https://github.com/ashvardanian/StringZilla
- 版本：5.1.2
- 许可证：Apache-2.0
- Conan 引用：`stringzilla/5.1.2`
- 适配路径：路径 B（贡献创新，知识草稿 E2174）

补丁为 HarmonyOS Clang 的 Arm 能力探测选择保守路径，并关闭 OHOS 下的自定义
libc 符号覆盖。上游 `forkunion` 子模块缺失，因此不把不可复现的完整测试套件
计为通过；消费者测试实际调用字符串搜索与相等比较 API。

详细统计、设备验证和知识草稿见 [5.1.2/notes.md](5.1.2/notes.md)、
[5.1.2/test_package/MANIFEST.yml](5.1.2/test_package/MANIFEST.yml) 和
`knowledge/drafts/E2174-draft-8DAC.*`。
