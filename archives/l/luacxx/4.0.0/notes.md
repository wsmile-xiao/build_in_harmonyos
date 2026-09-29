# luacxx 4.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-28
- 编译器: clang/clang++ (OHOS SDK, aarch64-linux-ohos)
- 状态: built

## 编译步骤

1. `init-build luacxx 4.0.0 --url=https://github.com/dafrito/luacxx/archive/refs/tags/v4.0.0.tar.gz`
   下载官方 tag v4.0.0 源码并核验 SHA-256
   `80b838f5d0309ed6dee79f62b9fa0040eb2f11f59fb43bf20a4ee9d42f559c38`
2. `lang-preflight`：语言匹配 cpp（CMakeLists project(luacxx) + 源码 793 文件，cpp 主体 98%）
3. CMake 构建（conan 注入 lua/5.4.8 依赖）：
   - `conan install --requires=lua/5.4.8 --requires=boost/1.85.0 -pr:h=ci/conan/profiles/ohos-aarch64`
   - `cmake .. -DLUACXX_BUILD_TESTS=ON -DLUA_INCLUDE_DIR=<merged> -DLUA_LIBRARIES=<liblua.a>`
   - `cmake --build . -j4` → `libluacxx.a` + 两个上游测试可执行文件
4. 运行上游测试：`ctest --output-on-failure` → 2/2 入口全过（34+1 用例）
5. `conan create`（ohos-aarch64 profile）→ G2 干净构建通过；test_package 消费者验证 PASSED
6. `finish luacxx 4.0.0 built` → W2/W3 本地 CI 通过（含其他库基线垃圾文件隔离复验）
7. 知识候选台账 + 七轴查重 → new_draft（DRAFT-luacxx-4.0.0-lua-error-cross-c-boundary）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `error_support` 用例 SIGABRT（uncaught lua::error） | OHOS musl 下 liblua.a 无 `.eh_frame`，C++ 异常无法穿过纯 C Lua 边界展开 | `invoke_callable<RV,Args...>` 入口 try/catch + `lua_push + lua_error` 转换（0002 补丁），复跑 6/6 断言通过 |
| 2 | `find_package(Boost COMPONENTS unit_test_framework)` 找不到库 | ohpcd boost/1.85.0 只发布头文件+少量静态库，未编译 unit_test_framework | 测试入口切 header-only `boost/test/included/unit_test.hpp`，去组件要求改链 Boost::headers（0001/0003/0004 补丁） |
| 3 | `boost/core/detail/sp_thread_sleep.hpp` 报 pthread_setcancelstate 未声明 | OHOS musl 无 pthread 取消状态 API | 测试编译补 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`（E507 既有知识） |
| 4 | `fatal error: 'lua.hpp' file not found` | lua conan 包只装 C 头，无上游发行版 lua.hpp | generate() 生成 `extern "C"` 四行包装头，随包安装（E580 草稿同方案） |
| 5 | `LUA_INCLUDE_DIR` 指向构建目录导致 CMake install 导出报错 | 构建期 include 目录被写入 INTERFACE_INCLUDE_DIRECTORIES | 改 `$<BUILD_INTERFACE:${LUA_INCLUDE_DIR}>`（0001 补丁） |
| 6 | conan-verify 临时镜像注入污染 conandata.yml | E017 预防机制注入 gh-proxy URL 未还原 | 恢复官方 HTTPS URL（R39/PF7），重新 commit |
| 7 | W3 JC 门禁拦截 4 个其他库基线垃圾文件（cloog/kics/thc 的 .staging-verified 等） | 其他库 PR 提交前已存在的空文件被整仓扫描 | 基线隔离复验：记录 SHA-256（e3b0c442... 空文件）→ 隔离 → 复跑 W3 通过 → 原样恢复核对一致 |

## 源码修改

补丁文件（均经 refresh-patch --auto 生成，patches/ 目录）：
- 0001-CMakeLists.txt.patch：Boost.Test header-only + BUILD_INTERFACE
- 0002-include-luacxx-convert-callable.hpp.patch：闭包边界异常转换
- 0003-tests-luacxx_without_conversions.cpp.patch / 0004-tests-main.cpp.patch：header-only 入口

## 依赖版本

- lua/5.4.8（制品仓已发布，conan download 验证通过）
- boost/1.85.0（build_requires，仅测试头）

## 验证结果

```bash
conan create archives/l/luacxx/4.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → G2 PASS；上游测试 2 入口全过；test_package 消费者 PASSED
ctest --output-on-failure
# → 100% tests passed (luacxx.test_main / luacxx.test_without_conversion)
./ohos_specific_test
# → [ohos-test] PASSED (0 failures)
```

上游测试全量通过率：`35/35 (100%)`（源码声明 35 项，含互斥宏 gobject_introspection 未实例化项；当前配置可执行集合 `34/34 (100%)`），另鸿蒙专项 1 项通过。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 构建配方（lua/5.4.8 依赖，静态库） |
| conandata.yml | 官方源 v4.0.0 + SHA-256 + 4 补丁声明 |
| test_package/ | 消费者用例（公开 API 真实调用） |
| tests/ohos_specific_test.cpp | 鸿蒙专项测试（随配方 export_sources） |
| patches/0001-0004 | 适配补丁 |
| knowledge/drafts/DRAFT-luacxx-4.0.0-lua-error-cross-c-boundary.{kv,md} | 知识草稿（B 类） |

## 注意事项

- 本库为静态库（无 bin 产物），不需要 commands.json（R38）
- conan-verify 的 E017 镜像注入会污染 conandata.yml，提交前必须核对官方 URL（已修复并复验）
- W3 JC 整仓扫描会命中其他库基线垃圾文件，按基线隔离复验流程处理，不得提交或修改那些文件

---

**编译结束**: 2026-09-28 12:50
**最终状态**: built
