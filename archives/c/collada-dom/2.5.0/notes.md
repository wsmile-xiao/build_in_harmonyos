# collada-dom 2.5.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-28
- 编译器: clang/clang++ (OHOS hnp 15.0.4, aarch64-linux-ohos)
- 状态: built（r03 配方重构：移除 -fuse-ld、接入共享 boost/1.90.0.1 的 libboost_filesystem 后，构建/打包/消费者运行验证通过）

## 编译步骤

通过 Conan 流水线完成（`conan create`，profile `ohos-aarch64`）：
1. `source()` 拉取官方 v2.5.0 归档（本地经 ghfast.top 已验证镜像下载，SHA-256 与官方一致：3be672407a7aef60b64ce4b39704b32816b0b28f61ebffd4fbd02c8012901e0d；交付配置 conandata.yml/manifest 保留官方 GitHub URL）
2. `apply_conandata_patches` 应用 7 个补丁（0001-0007）
3. CMake 配置 + 构建（OPT_COLLADA14/15=ON，其余组件 OFF；clang -fPIC）
4. `package()` 安装头文件与 `libcollada-dom2.5-dp.so`
5. `test_package` 编译并链接消费者（test_collada_dom）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Boost.Filesystem 未定义符号 | registry 的 `boost/1.90.0` 为头文件版包（operations.hpp 仅外部声明 detail 文件系统函数、无 libboost_filesystem），消费者会留未定义符号；r01 的"1.74 起 header-only"判断对 OHOS registry 该包不成立 | r03 改用共享变体 `boost/1.90.0.1`（含 libboost_filesystem.so），0001 补丁 `find_package(Boost CONFIG REQUIRED COMPONENTS filesystem)` + 链接 `Boost::filesystem` 目标 |
| 2 | `<boost/filesystem/convenience.hpp>` 已删除 | Boost >= 1.80 移除该头 | 0002/0003 补丁改引 `<boost/filesystem.hpp>` / `<dae.h>` 移除该 include |
| 3 | 静态模块库链入共享库 relocation 失败 | OHOS clang 下 `CMAKE_COMPILER_IS_GNUCC` 为假，未加 -fPIC | 0001 补丁为 clang 分支追加 `-fPIC` |
| 4 | libxml2 找不到 | 上游非 MSVC 分支对 libxml2 无内嵌回退（FATAL_ERROR） | 0004-0007 补丁 + conanfile 声明 `libxml2/2.15.3` 依赖，CMakeDeps 走 `LibXml2::LibXml2` |
| 5 | 本地 pcre 建成共享库，产生损坏相对 DT_NEEDED | 父工程 `BUILD_SHARED_LIBS=ON` 泄漏到 pcre 子工程，`libpcre_local.so` 带 `external-libs/pcre-8.02/` 相对路径无法解析 | 0001 补丁在 `add_subdirectory(pcre-8.02)` 前强制 `BUILD_SHARED_LIBS OFF`，pcre 静态内嵌（上游本就传 `-DPCRE_STATIC`） |
| 6 | test.cpp 引用不存在 API | `dae/modules/dom150/domCOLLADA.h`、`daeConstants`、`domCOLLADAProxy::getDom()` 在 2.5.0 均不存在 | test.cpp 改为真实 API：`dae.load(mem://, buf)` + `dae.getRoot()`（返回 `daeElement*`）+ `dae.getDatabase()->getElementCount()` |
| 7 | test() 运行时 .so 加载失败 | `cmake.test()`（CTest）不激活 conanrun 环境 | test_package 按 E298 改为显式 `self.run(..., env="conanrun")` |
| 8 | dlopen Permission denied | 配方注入 `-fuse-ld=/data/service/hnp/bin/ld`，该链接器产出的 .so 被 OHOS musl 加载器以 EACCES 拒绝（对照：默认链接器产物可加载） | r03 移除该注入，使用默认链接器 |
| 9 | 加载后 relocation 缺 boost 符号 | boost/1.90.0 头文件版无 libboost_filesystem | r03 改共享 boost/1.90.0.1 + CMakeDeps `Boost::filesystem` 链接 |

## 源码修改

补丁文件（patches/0001-0007，由 refresh-patch 生成）：
- 0001 CMakeLists.txt：cmake 最低版本 3.5 + boost 共享组件（find_package(Boost CONFIG COMPONENTS filesystem) + Boost::filesystem 链接）+ clang -fPIC + libxml2 target 处理 + pcre 静态化
- 0002 dom/include/dae.h：移除 convenience.hpp
- 0003-0007：daeErrorHandler/daeUtils/daeZAE 等源文件修复

## 依赖版本

- boost/1.90.0.1（共享变体，含 libboost_filesystem.so）
- libxml2/2.15.3

## 验证结果

- conan create（lib 主包）：**通过**（构建 + 安装 lib/include）
- conan create（test_package）：编译+链接+**运行通过**——默认链接器 + 共享 boost libboost_filesystem 后，test 二进制加载 libcollada-dom2.5-dp.so 并实际执行 DAE API（dae.load + getRoot + getElementCount）
- W3 本地 CI：基线隔离（git 索引级）后 JC_RESULT=pass；随后 conan create 通过（r03）
- G0 干净构建验证：`clean_verify` 对 CMake 工程误跑 `./configure`（exit 127），工具层限制，非阻塞

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2 配方（共享 boost/1.90.0.1 + libxml2 依赖，无 -fuse-ld） |
| conandata.yml | 源码/补丁清单（sha256 与官方一致） |
| patches/0001-0007 | 平台适配补丁 |
| test_package/ | 消费者测试（真实 API 用法） |
| manifest.yaml | 版本 manifest |

## 注意事项

- 本机官方 GitHub 直连超时，本地下载经 ghfast.top 已验证镜像（SHA-256 与官方一致）；交付配置 conandata.yml 与 manifest 均保留官方 GitHub URL，无镜像前缀。
- 不得恢复 `-fuse-ld=/data/service/hnp/bin/ld` 注入（其产物被 OHOS 加载器拒绝）；boost 必须用含 libboost_filesystem 的共享变体。
---

**编译结束**: 2026-08-28 23:35
**最终状态**: built
