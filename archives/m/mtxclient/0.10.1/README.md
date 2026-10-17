# mtxclient 0.10.1

| 项目 | 值 |
|------|-----|
| 状态 | 🟡 built（配方/补丁/test_package + 本机门禁全通过；W0 依赖全部已发布；设备 conan create 待空闲窗口） |
| 构建系统 | CMake（C++20） |
| 源码 | `https://github.com/Nheko-Reborn/mtxclient/archive/refs/tags/v0.10.1.tar.gz` |
| sha256 | `203be46a08e1dc6cfc068d0911f3b09976f48e4cc4302c3517b9c0f4e53631e3` |
| 补丁 | 2 个（olm 包名小写化、gtest 改走 pkg-config） |
| 产物 | 库（`libmatrix_client.so.*` + 头文件 + `MatrixClient` CMake 包） |

## 快速使用

```python
self.requires("mtxclient/0.10.1")
```

```cmake
find_package(MatrixClient CONFIG REQUIRED)
target_link_libraries(app PRIVATE MatrixClient::MatrixClient)
```

## 文件

```
0.10.1/
├── conanfile.py                  # 主配方（含 ctest 离线子集执行 + pkgconf tool_requires）
├── conandata.yml                 # 源码 URL + sha256 + 2 个补丁声明
├── patches/
│   ├── 0001-cmakelists-lowercase-olm-package.patch
│   └── 0002-cmakelists-gtest-targets.patch
├── test_package/                 # 消费者视角测试（36 项断言，纯离线）
│   ├── conanfile.py
│   ├── CMakeLists.txt
│   ├── test_package.cpp
│   └── MANIFEST.yml
├── manifest.yaml                 # 版本级元数据
├── notes.md                      # 适配笔记（W0 结果、分析结论、下一步命令）
└── reports/
    ├── local-validation.md       # 本机验证报告（含设备探针与复现命令）
    └── adaptation-analysis.md    # 阻塞点与可行性分析
```

## 关键适配点

1. **C++20 必需** —— 上游 `mtx/identifiers.hpp` 用 `std::strong_ordering` + `operator<=>`，
   profile 的 `cppstd=17` 已由配方覆盖为 20。
2. **系统没有 pkg-config** —— 上游用 `pkg_check_modules` 探测 5 个依赖；OHOS 镜像既无
   `pkg-config` 也无 `pkgconf`，配方以 `tool_requires("pkgconf/3.0.6")` 引入并固定
   `PKG_CONFIG_EXECUTABLE`。**这是本库在设备上最容易被忽略的失败点。**
3. **两个可移植性补丁**（只改 `CMakeLists.txt`）—— olm 包名/目标名小写化；
   gtest 测试目标改用当前名 `GTest::gtest` / `GTest::gtest_main`（1.14 删除了旧名）。
4. **已知运行期限制** —— ohpcd `libcurl/8.5.0` 无 TLS 后端，真实 homeserver 的 HTTPS
   通信会返回 `CURLE_UNSUPPORTED_PROTOCOL`；不影响编译、链接与离线 API。

## 下一步

依赖齐备，只差设备空闲窗口：

```sh
CI_PACKAGES="archives/m/mtxclient/0.10.1" zsh ci/conan/build_and_test.sh
```

详见 `notes.md` §六 与 `reports/adaptation-analysis.md` §4。
