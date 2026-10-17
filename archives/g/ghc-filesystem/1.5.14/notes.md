# ghc-filesystem 1.5.14 — 适配笔记

## 官方来源核验（bootstrap R01）

- 官方仓库: https://github.com/gulrak/filesystem (gulrak/filesystem)
- 正式版本: v1.5.14 (GitHub 正式 release tag)
- release commit: `8a2edd6d92ed820521d42c94d179462bf06b5ed3`
- 官方 tarball sha256: `3b28457a844b006d2dbc415c201b1fa74601f3b6c6ba5cb4bf4c16b6889f739d`
- 源码内版本自检: `include/ghc/filesystem.hpp` 定义 `GHC_FILESYSTEM_VERSION 10514L`（= 1.5.14）
- 许可证: MIT (LICENSE)

## 适配形态

- header-only 库：上游 CMake 以 INTERFACE target `ghc_filesystem` 交付，无编译产物
- package 内容：`include/ghc/*.hpp`（filesystem.hpp / fs_fwd.hpp / fs_impl.hpp / fs_std*.hpp）+ LICENSE
- 无系统同名库、无运行时依赖，OHOS PC (aarch64) 直接 include 使用即可（R26/R40 不适用）

## 备注

- 首轮 Adapt: 配方骨架已建立（conanfile.py + conandata.yml + test_package），本地验证待 conan create 确认
## r03 上游测试逐入口台账（evidence closure，2026-08-31）

编译/运行均在本机 aarch64 host 用 OHOS 工具链 clang++（/data/service/hnp/bin/clang++，-std=c++17 -I include -I test）。
日志根目录（绝对）：/storage/Users/currentUser/tmp/ghc-fs-check/ledger/

| 入口 | 命令 | cwd | 退出码 | 首错 | 日志(绝对路径) | 日志 SHA-256 | 缺失前置 | 阻塞归属 | 恢复条件 |
|------|------|-----|--------|------|----------------|--------------|----------|----------|----------|
| filesystem_test.cpp | clang++ ... test/filesystem_test.cpp -o filesystem_test && ./filesystem_test | ledger/ | 编译0/运行18 | fs::copy create_hard_links: Operation not permitted | /storage/Users/currentUser/tmp/ghc-fs-check/upstream_test.log | 0065dbdeac9b84a9d7253c79652384447012d970f1ea1e0e839ae9d18d72eda6 | 无 root；tmpfs/hmfs 不支持 hard link/mkfifo；chmod 不生效 | 平台限制（E046 chmod 不生效类），非库缺陷 | 在支持 hardlink/fifo 且可写权限的宿主运行 |
| exception.cpp | clang++ -std=c++17 -fno-exceptions -I include test/exception.cpp -o exception_test && ./exception_test | ledger/ | 编译0/运行0 | 无 | /storage/Users/currentUser/tmp/ghc-fs-check/ledger/exception_test.log | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 无 | 通过 | - |
| multi1.cpp+multi2.cpp | clang++ ... test/multi1.cpp test/multi2.cpp -o multifile_test && ./multifile_test | ledger/ | 编译0/运行0 | 无 | /storage/Users/currentUser/tmp/ghc-fs-check/ledger/multifile_test.log | cb01fccae940c24bb47023fb531e38bb72a636d6edd6662ecd3d09e6231608e6 | 无 | 通过 (8 assertions / 2 cases) | - |
| fwd_test.cpp+impl_test.cpp | clang++ ... test/fwd_test.cpp test/impl_test.cpp -o fwd_impl_test && ./fwd_impl_test | ledger/ | 编译0/运行18 | 同 filesystem_test（复用全套 70 cases） | /storage/Users/currentUser/tmp/ghc-fs-check/ledger/fwd_impl_test.log | 183d77a08d452122aea41584547a499d3bdec531e69a0c4c6f429045c8889496 | 无 root；同上平台限制 | 平台限制（E046 类），非库缺陷 | 同上 |

统计：实际运行入口 4 个（filesystem_test、exception、multifile、fwd_impl），其中 2 个全过、2 个含平台受限失败；
未运行/不可运行入口：无（四个入口均已尝试并记录）。未修改任何上游测试断言；未使用 build-tests=false 或宽泛排除伪造通过。
---

**编译结束**: 2026-08-31 13:38
**最终状态**: built
