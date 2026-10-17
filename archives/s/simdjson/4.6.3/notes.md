# simdjson 4.6.3 — 适配笔记

> 档案创建时间: 2026-04-26
> 最后更新: 2026-08-22
> 当前状态: built (Conan 配方已生成并验证)

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | simdjson |
| 版本 | 4.6.3 |
| 构建系统 | CMake |
| 源码 URL | https://github.com/simdjson/simdjson/archive/refs/tags/v4.6.3.tar.gz |
| SHA256 | bde0c42f43899c4c5c48be826c09abd22500ed537b89f16b3cced5eec477c263 |

## 二、编译过程

### Phase 2: 编译
- [x] cmake configure 完成
  - 编译器: clang 15.0.4
  - CMAKE_BUILD_TYPE=Release
  - BUILD_SHARED_LIBS=ON
  - SIMDJSON_INSTALL=ON
  - cmake 输出 "System is unknown to cmake" 警告，不影响构建
- [x] make 编译完成 (无错误)
- [x] make install 完成

### Phase 3: 测试
- [x] smoke test: 解析 JSON `{"test":123}` 成功，输出 `test value: 123`

## 三、依赖
无外部依赖。simdjson 自包含，仅依赖系统 pthread。

## 四、适配要点
1. simdjson 是纯 C++ 库，使用 CMake 构建系统
2. CMake 检测到 OHOS 平台时输出 "System is unknown to cmake" 警告，但不影响构建
3. 构建产物: libsimdjson.so (shared) / libsimdjson.a (static)
4. 头文件: simdjson.h (单头文件，包含所有 API)
5. 需要链接 pthread (Linux/OHOS)

## 五、Conan 配方
- conanfile.py 生成完毕
- conandata.yml 包含正确的 SHA256
- test_package/ 使用 simdjson on-demand API 验证 JSON 解析功能 (R34 实质依赖)
- 默认 static 链接 (default_options shared=False)
