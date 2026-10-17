# imageinfo 2.0.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only 库，`imageinfo` 为 INTERFACE target + CLI 工具）
- 编译日期: 2026-09-22
- 编译器: clang/clang++（OHOS aarch64，libc++，clang 15.0.4）
- 状态: built（conan-verify G0-G4 全部通过；制品未发布，由 PR 合并后 CI 发布）

## 编译步骤

```bash
# 上游源码：官方 tag v2.0.0（commit 126b391916169dc27bcdc3e555c7f73a95403bc2）
# release 归档 SHA-256: ca033b939dae24e990389781728ce948e09665f45a2be70d4ac1aff83931d0eb
cmake -S . -B build \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DIMAGEINFO_BUILD_TOOLS=ON -DIMAGEINFO_BUILD_TESTS=ON -DIMAGEINFO_BUILD_INSTALL=ON
make -C build -j2          # 构建 imageinfo（CLI）与 imageinfo_tests
ctest --output-on-failure  # 上游测试 1/1 通过
make -C build install DESTDIR=... # staging 隔离安装

# Conan 验证（ohos-aarch64 profile）
conan create archives/i/imageinfo/2.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

- `source()`: 下载官方 tag release 归档，strip_root 解压
- `build()`: cmake configure（`IMAGEINFO_BUILD_TOOLS/TESTS/INSTALL=ON`）→ 构建 →
  运行上游 `imageinfo_tests`（解析 images/ 下真实样例，约 200 断言），输出
  `HMBS_UPSTREAM_TEST_RESULT` 标记
- `package()`: 拷贝 `include/imageinfo.hpp` + LICENSE，`cmake.install()` 安装 CLI
- `test_package`: `parse<RawDataReader>` 解析 1x1 PNG 内存字节，校验 kFormatPng 与尺寸

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 `github.com` 归档超时（urllib Operation timed out） | 本机直连 github.com:443 不稳定 | 改用 `codeload.github.com` 下载官方归档（内容一致），并确认 SHA-256；conan-verify 的 E017 镜像注入（ghfast.top）可正常完成 |
| 2 | conan-init 生成 autotools 模板配方 | 构建系统按 URL 猜测为 autotools，与实际 CMake 不符 | 手工改写为 CMake header-library 配方（参考 abletonlink），显式声明 IMAGEINFO_BUILD_* 选项 |
| 3 | 上游 ctest 二进制定位 | Makefiles 生成器产物在 build 根目录而非 bin/ | 配方内递归定位 imageinfo_tests（`_find_test_binary`） |

## 源码修改

无补丁（header-only 库，零源码改动）。patches/ 为空。

## 依赖版本

无第三方依赖（header-only，零依赖）。

## 验证结果

```bash
ctest --output-on-failure        # 1/1 通过（imageinfo_tests）
conan-verify G0-G4               # 全部 PASS（含 conan create 干净构建）
test_package 消费者测试          # 1/1 通过（test_imageinfo，png 1x1）
W3 本地 CI 模拟（setup+build_and_test.sh）  # 通过
```

## 注意事项

- 本机 chmod 移除写位不生效（HMFS/SELinux 平台限制，E046），知识快照只读性由执行端纪律保证并记录审计
- `github.com` 直连超时属网络环境问题（E017 类），CI 镜像注入可覆盖
- gen_summary 报 `'str' object has no attribute 'append'`：仓库级既有缺陷（主仓库同样失败），
  非本次归档引起，且 SKILL 标记该步骤非致命，不影响交付
- 依赖项：本库无依赖，W0 预检通过（preflight_check.sh 无依赖声明）
---

**编译结束**: 2026-09-22 17:09
**最终状态**: built
---

**编译结束**: 2026-09-22 17:21
**最终状态**: built
