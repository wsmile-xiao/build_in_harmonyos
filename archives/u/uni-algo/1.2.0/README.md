# uni-algo

**Unicode Algorithms Implementation** — 单一作者的 C++ Unicode 算法库（UTF-8/16/32
相互转换与严格校验、大小写映射、NFC/NFD/NFKC/NFKD 归一化、字素/词/句/行断句、
码点属性、Script 检测、BCP47 语言标签与排序）。零第三方依赖，只需 C++17 标准库。

- 上游：<https://github.com/uni-algo/uni-algo>
- 许可证：Public Domain (Unlicense) 或 MIT，二选一
- Unicode 版本：15.1.0

## HarmonyOS PC (aarch64) 适配要点

- 版本：1.2.0（官方 tag `v1.2.0`；`codeload.github.com` 与 `github.com/archive`
  同一 tarball，437340 B / SHA-256 `f2a1539cd8635bc6088d05144a73ecfe7b4d74ee0361fabed6f87f9f19e74ca9` 已对拍一致）
- 构建系统：CMake。**上游是两个独立 CMake 工程**——根工程出 `libuni-algo.a`，
  `test/` 自带 `project()`，上游 CI 用 `cmake -S test -B build && ctest` 跑官方测试
- 交付形态：纯静态库（`package_type = static-library`，`BUILD_SHARED_LIBS=OFF`），
  产物 `lib/libuni-algo.a` + `include/uni_algo/**.h` + `licenses/LICENSE.md`；
  无 `bin/`，因此不需要软件级 `commands.json`（L0k）
- 上游官方测试在 `conanfile.py` 的 `build()` 内真实执行（不是用 test_package 冒充）：
  第二个工程必须显式带上 conan 的 `conan_toolchain.cmake`，否则会退回宿主机编译器
- `DOWNLOAD_UNICODE_TEST_FILES` 保持上游默认 OFF：它会在 configure 阶段从 unicode.org
  拉 3 个数据文件且下载失败即 `FATAL_ERROR`，离线环境不可开；随之有 2 个
  `SKIP: ... with test files` 分区，原因已在 `test_package/MANIFEST.yml` 逐条声明
- 上游测试工程对 GNU/Clang 无条件加 `-Werror`；profile 里 `compiler.cppstd=17`
  会让该工程按 C++17 编译（上游 CI 自己是 C++20），两种标准下 15 个 `DONE` 分区结果一致
- OHOS clang 15 + musl 下一次编过，**未修改上游源码**（`patches: {}`）
