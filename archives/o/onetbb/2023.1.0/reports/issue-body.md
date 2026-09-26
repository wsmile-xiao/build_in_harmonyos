申请人：2301_80739235
队伍名称：天天开心
申请日期：2026/09/05
库名称：onetbb
版本：2023.1.0

申请原因：为 OpenHarmony PC aarch64 提供 oneTBB 2023.1.0 Conan 适配，补齐 POTENTIAL_SIMPLE 拓扑中的 libtbb-dev 目标库。

知识库查重情况：已检索 knowledge/graph、knowledge/drafts、knowledge/doc、knowledge/operations；未发现本次版本化共享库物理链接名与 CMakeDeps 元数据绑定问题的等价可复用条目。

可复用说明：新增 E2184 草稿，说明 CMake 安装产物使用版本化链接文件名时，cpp_info.libs 必须绑定物理 basename，同时保留逻辑 CMake target；适用于同类 Conan/CMake 库，需在 producer 与真实 consumer 两侧复核。

适配路径：路径 A（基础适配）/ 路径 B（知识库扩展）
当前状态：待创建 PR，等待平台 CI 与审核流程。
