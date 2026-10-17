# libmusicbrainz5

MusicBrainz Web Service 客户端库（C/C++ 绑定）。

- 上游仓库: <https://github.com/metabrainz/libmusicbrainz>
- 项目主页: <https://musicbrainz.org/doc/libmusicbrainz>
- 许可证: LGPL-2.1
- 构建系统: CMake

## 版本索引

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| `5.1.0-git20150707` | published | 2026-09-17 | 上游 2015-07-07 快照（对应 Debian 源包 `5.1.0+git20150707-N`） |

## OHOS 适配要点

1. **CMake 4.x 兼容**：上游 `cmake_minimum_required(VERSION 2.6)`，需以命令行参数
   `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 配置（写在 toolchain 变量中无效）。
2. **依赖发现**：上游 `cmake/modules/FindLibXml2.cmake` / `FindNeon.cmake` 仅使用
   `FIND_PATH` / `FIND_LIBRARY` 搜索系统路径，需通过 `CMAKE_INCLUDE_PATH` /
   `CMAKE_LIBRARY_PATH` 注入 Conan 依赖的 include/lib 目录。
3. **不要前置 Conan libxml2 到 `LD_LIBRARY_PATH`**：OHOS SDK 的 `lld` 自身依赖
   SDK `llvm/lib` 下的 `libxml2.so.16`；若 Conan libxml2 的 lib 目录排在前面，
   lld 会加载 ABI 不兼容的同名库并报 `symbol not found`。正确顺序为
   SDK `llvm/lib` 前置、Conan 依赖目录追加。
4. **补丁（3 个）**：
   - 移除 `src/CMakeLists.txt` 中 `DEPENDS` 的 `*.inc` 字面 glob
     （`make` 不展开通配符，报 `No rule to make target`）；
   - 适配 libxml2 2.15.x 的 `xmlGetLastError()` 返回 `const xmlError *` 签名变化；
   - 显式设置共享库 `DT_SONAME`（OHOS 工具链下 CMake 未按上游 `SOVERSION` 生成），
     SONAME 取不带版本号的实际文件名。
5. **产物**：该快照将 C 接口拆分，产出 `libmusicbrainz5.so`（C API）与
   `libmusicbrainz5cc.so`（C++ API）两个库。

## 上游测试说明

上游 CMake **未接入任何自动化测试框架**（`enable_testing()` / `add_test()` 为 0 处）。
`tests/` 下仅有两个手工演示程序 `ctest`（C API）与 `mbtest`（C++ API），
二者均硬编码访问线上 `musicbrainz.org` / `test.musicbrainz.org` 服务，
需网络与认证凭证，无法作为离线回归手段。

本适配以 `test_package/` 中的消费者用例（C++ / C API 构造、getter、
句柄生命周期）作为验证手段，详见
[`5.1.0-git20150707/reports/upstream-test-report.md`](5.1.0-git20150707/reports/upstream-test-report.md)。

## 消费方式

```python
self.requires("libmusicbrainz5/5.1.0-git20150707")
```

```cmake
# 上游未提供 CMake config 包，亦无可靠 CMakeDeps 目标；
# 推荐通过 pkg-config 或手工指定 include/lib 消费。
find_package(PkgConfig REQUIRED)
pkg_check_modules(MB5 REQUIRED libmusicbrainz5)
```
