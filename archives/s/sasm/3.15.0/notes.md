# sasm 3.15.0 适配笔记

## 编译环境
- 构建系统: cmake（patches/0001-CMakeLists.txt.patch，由上游 qmake SASM.pro 等价改写）
- 编译日期: 2026-10-01
- 编译器: clang 15.0.4（ci/conan/profiles/ohos-aarch64）
- 状态: built（PR 合并 upload 成功后转 published）

## 编译步骤

1. `conan create archives/s/sasm/3.15.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing --user=ohpcd --channel=stable`
2. 依赖 qt/5.15.19 直接复用制品仓 OHOS 二进制（os.version=6.0, cppstd=17, libcxx=libc++）
3. test_package 以 QT_QPA_PLATFORM=offscreen 实际执行 sasm 二进制（8s 存活判定）

## 上游测试清点（R51）

- 上游构建系统 qmake（SASM.pro）：无 `test`/`check` 目标（`grep -n "^test\|check" SASM.pro` 无命中）。
- 源码树无 tests/ 或 autotest 目录（`ls` 顶层仅有源文件/资源/singleapplication/Linux/Windows/BSD）。
- 结论：上游测试数 = 0，无可运行上游测试。适配后新增消费者视角测试 test_sasm.sh（3 断言，test_package/MANIFEST.yml 已如实申报 upstream_tests: []）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | qtlockedfile.cpp 编译报 use of undeclared identifier 'QtLockedFile' | qtlocalpeer.cpp 在 QtLP_Private 命名空间内 #include qtlockedfile*.cpp（源码内嵌），单独编译使类定义落命名空间外 | CMakeLists 严格按上游 .pri 的 SOURCES：只编 qtsingleapplication.cpp + qtlocalpeer.cpp（知识草稿 E429-draft-B1CC） |
| 2 | conan create 反复卡源码下载 | GitHub 直连/ghfast 镜像抖动；finish 镜像注入致 conandata 导出内容漂移 | 按 conandata sha256 预种 core.sources:download_cache（键=sha256），一次成功下载永久复用 |

## 源码修改

- patches/0001-CMakeLists.txt.patch：新增 CMakeLists.txt（qmake→CMake 等价改写，AUTOMOC/AUTOUIC/AUTORCC，Qt5 Core/Gui/Widgets/Network），无平台宏。

## 依赖版本

- qt/5.15.19（制品仓已发布 OHOS 二进制）

## 验证结果

```bash
conan create archives/s/sasm/3.15.0 -pr:h=ci/conan/profiles/ohos-aarch64 ... # 全绿
# test_package: PASS: sasm launched and ran headless (offscreen), still alive after 8s
```

## 注意事项

- SASM 运行需外部汇编器（nasm/gas/fasm/masm）与 gdb，本包仅交付 IDE 二进制。
- GitHub release tarball 为即时生成产物，直连易超时/截断；哈希须以 conan 完整下载体（22MB）校验。

## 最终状态

COMPLETED — W3 本地 conan create 全绿（test_package 3/3 断言）、W4 审计通过（P0=0 P1=0）、产物已打包 packaging/sasm-3.15.0-ohos-aarch64.tar.gz。状态 built，PR 合并 upload 成功后转 published。
