# OpenCC 1.1.9 编译笔记

## 基本信息
- 软件名：OpenCC (Open Chinese Convert)
- 版本：1.1.9
- 构建系统：CMake
- 描述：开源中文转换工具，支持简繁转换
- 上游仓库：https://github.com/BYVoid/OpenCC

## 编译日志

### 初始化
- 下载源码：GitHub BYVoid/OpenCC ver.1.1.9
- 解压目录：$HOME/tmp/builds/opencc-1.1.9.work
- 构建系统：CMake

### 编译过程
- 编译器：Clang++ 15.0.4
- 构建类型：Release
- 构建选项：静态库（BUILD_SHARED_LIBS=OFF）
- 编译时间：2026-08-07
- 编译状态：成功

### 遇到的问题
1. **动态库加载失败**：首次使用共享库构建时，opencc_dict 工具无法加载 libopencc.so
   - 解决方案：改用静态库构建（BUILD_SHARED_LIBS=OFF）
2. **字典路径问题**：staging 目录中字典文件路径不匹配
   - 解决方案：安装到实际前缀进行测试

### 功能验证
- 版本输出：OpenCC 1.1.9
- 简繁转换测试：通过
  - 输入：简体中文 → 输出：繁体中文
  - 输入：简体中文 → 输出：簡體中文

### Conan 适配 (2026-08-07)
- 生成 conanfile.py + conandata.yml + test_package/
- 静态库构建，无外部依赖（所有依赖均为内嵌：marisa, rapidjson, tclap, darts-clone）
- 构建产物：
  - 库文件：libopencc.a, libmarisa.a
  - 可执行文件：opencc, opencc_dict, opencc_phrase_extract
  - 字典文件：16个 .ocd2 文件
  - 配置文件：14个 .json 文件
- test_package 使用 SimpleConverter API 进行简繁转换验证

---
**最终状态**: built（已构建，Conan 配方已生成并通过验证）
---

**编译结束**: 2026-08-07 06:39
**最终状态**: built
