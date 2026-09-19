# bzip3 1.5.4 适配笔记

## 编译环境
- 构建系统: cmake（历史经验 1.4.0/1.5.3 均用 CMake；autotools 有 HMDFS 临时目录问题）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤
```bash
cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DBZIP3_BUILD_APPS=ON \
  -DBZIP3_ENABLE_PTHREAD=ON \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
cmake --build build -j2
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure 失败: bzip3-config.cmake.in does not exist | 1.5.4 release tarball 打包遗漏该文件（上游 git tag 1.5.4 存在），CMakeLists.txt:102 configure_file 必须读它 | patches/0001-bzip3-config.cmake.in.patch 还原上游 git 内容 |
| 2 | bz3_compress 返回 BZ3_ERR_DATA_TOO_BIG(-6) | libbz3 高层 API 的 *out_size 是 in/out 参数，调用前必须初始化为输出缓冲区容量（libbz3.h 98-99/108 行） | 测试/消费者用例中先置 comp_size=bound、decomp_size=in_size+余量 |
| 3 | W3 L0k 门禁失败: commands.json 缺 1.5.4 版本 | R38 CLI 工具声明：bzip3 提供 bzip3/bunzip3/bz3cat 等 CLI，须在软件级 commands.json 声明每个版本 | archives/b/bzip3/commands.json versions 补 1.5.4 |
| 4 | CMake 平台探测: "System is unknown to cmake" | OHOS 平台非 CMake 内置 | 非阻塞警告（1.4.0/1.5.3 同），构建成功 |

## 依赖版本
- 无第三方依赖（仅 libc + pthread）
- libsais 为内嵌 3rdparty（静态包含，无外部依赖）

## 验证结果
```bash
bzip3 --version  # bzip3 1.5.4 ✅
./ohos_bzip3_roundtrip  # OHOS_BZIP3_TEST PASS ✅
./consumer_bzip3_app    # consumer OK ✅
```

## 交付物
| 文件 | 说明 |
|------|------|
| libbzip3.a | 静态库（libbz3 API） |
| bzip3 + bunzip3/bz3cat/bz3grep/bz3less/bz3more/bz3most | CLI 工具 |
| libbz3.h | 公开头文件 |

## 注意事项
- 官方源码无任何自动化测试（见 reports/upstream-test-enumeration.md），真实可执行验证由鸿蒙专项测试与 test_package 承担
- bzip3 上层 CMake 目标为 bzip3::bz3（conanfile package_info.cmake_target_name），test_package 消费者必须链接 bzip3::bz3
---

**编译结束**: 2026-09-19 03:36
**最终状态**: published
