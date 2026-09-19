# genann 1.1.1 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile，无 configure）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（--target=aarch64-linux-ohos）
- 状态: published

## 编译步骤

1. 下载官方 tag v1.1.1 tarball（GitHub codeplea/genann，SHA-256
   66971187438de20c33ddd49d8d610e6d77c96f64d5345cdfbfc8efa913b71ced）。
2. 交叉编译验证：`make test` / `make all`，CFLAGS 覆盖为
   `-Wall -Wshadow -O2 -fPIC --target=aarch64-linux-ohos --sysroot=<ohos-sdk sysroot>`。
3. 上游测试：`./test` → ALL TESTS PASSED (521586/521586)，13/13 用例。
4. 鸿蒙专项测试：`tests/ohos_specific_test.c` 编译运行 ALL PASSED。
5. Conan：conanfile.py 用 GnuToolchain 生成工具链；build() 中 make -j1 test，
   package() 中 ar 归档 libgenann.a 并安装头文件；test_package 用 CMake 消费
   genann::genann 目标，消费者 XOR 分类 4/4。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CFLAGS `-march=native` 交叉编译失败 | native 指令集对 aarch64 目标无效 | 配方 GnuToolchain 覆盖 CFLAGS（aa3d 范式） |
| 2 | 上游无库 install 目标 | genann 设计为"把 genann.c/.h 加进项目" | 配方编译 genann.o 后 `ar rcs libgenann.a`，安装 include/ + lib/ |
| 3 | GitHub 主站连接超时（codeload 可用） | 网络对 github.com 主站不稳定 | 用 codeload 官方直链下载同一 tag，SHA-256 核验一致 |
| 4 | /tmp 只读满盘（HMDFS） | OHOS 设备 /tmp 为只读 | 使用 $TMPDIR=/storage/Users/currentUser/tmp 专用可写目录 |

## 依赖版本

- 无外部依赖（仅 libm，由 OHOS SDK sysroot 提供）

## 验证结果

```bash
$ ./test
ALL TESTS PASSED (521586/521586)
$ ./ohos_specific_test
OHOS-SPECIFIC TEST: ALL PASSED
$ conan create . --build=missing -pr:b default -pr:h ohos-aarch64
consumer_test: XOR classification correct 4/4  (exit 0)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | GnuToolchain + Makefile 构建，静态库打包 |
| conandata.yml | 官方 URL + SHA-256 |
| test_package/ | 消费者验证（CMake + genann::genann） |
| tests/ohos_specific_test.c | 鸿蒙专项测试 |
| reports/upstream-test-ledger.md | 上游测试双口径台账（13/13 = 100%） |

## 注意事项

- 上游 Makefile 无 install 目标，配方内自行归档静态库。
- `make` 并行度用 -j1（HMDFS jobserver mkfifo 限制，R9）。
- 上游 tag 为 `v1.1.1`（带 v 前缀）。
---

**编译结束**: 2026-09-19 04:11
**最终状态**: published
