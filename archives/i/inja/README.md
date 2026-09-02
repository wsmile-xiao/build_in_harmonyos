# inja

inja 3.5.0 是带嵌入式 nlohmann::json 的 C++17 header-only 模板引擎。本适配
提供 `pantor::inja` CMake consumer target。

## HarmonyOS 适配

- 上游仓库：https://github.com/pantor/inja
- 版本：3.5.0
- 许可证：MIT
- Conan 引用：`inja/3.5.0`
- 适配路径：路径 A（基础适配）

配方启用 embedded JSON，避免构建时下载或查找外部 nlohmann_json；同时构建并
执行上游 normal/single-header 两套测试目标。

详细测试统计见 [3.5.0/notes.md](3.5.0/notes.md) 和
[3.5.0/test_package/MANIFEST.yml](3.5.0/test_package/MANIFEST.yml)。
