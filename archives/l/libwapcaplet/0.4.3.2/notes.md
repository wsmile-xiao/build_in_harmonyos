# libwapcaplet 0.4.3.2 适配笔记

## 编译环境
- 构建系统: makefile（NetSurf Makefile → standalone Makefile 替换）
- 编译日期: 2026-09-01（本轮补全 conan 配方并真实验证）
- 编译器: clang/clang++ (15.0.4, /data/service/hnp/bin)
- 归档工具: llvm-ar / llvm-ranlib
- 状态: published

## 编译步骤（本轮真实执行，2026-09-01）

1. `ohc-run.py init-build libwapcaplet 0.4.3.2 --url=<github archive>`：下载
   `libwapcaplet-c7c128d3...tar.gz`（github archive，sha256 e1e1f6cc...11e1 实测一致），
   双轨解压到 `~/tmp/builds/libwapcaplet-0.4.3.2.{orig,work}`
2. `pre-analysis`：makefile 构建系统，无图形/音视频/系统集成依赖，无平台障碍
3. `conan-init` 生成配方骨架 → 手工改写为生产级配方：
   - `conanfile.py`：`make CC/AR/RANLIB`（R33，从 Conan conf 取编译器）+ `-j1`（R9/E074）；
     `make install PREFIX=<package_folder>` 打包；`package_info.libs=["wapcaplet"]`
   - `test_package/`：CMake 消费者测试，真实调用 lwc_string_* API（R34，16 个断言）
4. 手动验证：独立 Makefile 编译出 `libwapcaplet.a`（6562 bytes, aarch64），
   `make install PREFIX=/ DESTDIR=<stage>` 产出完整目录结构
5. `conan-verify`：G0-G4 + L2/L4/L5 全部 PASS（G2 = 真实 `conan create` 编译+测试通过）
6. `finish published`：W3 本地 CI 模拟通过（setup.sh + build_and_test.sh），
   `.ci-result.json` 由 W3 门禁真实写入（exit_code=0，含日志完整性哈希）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | NetSurf 构建系统依赖 (`NSSHARED`) | 原始 Makefile include `$(NSSHARED)/makefiles/Makefile.tools`，netsurf-buildsystem 包不可用 | 补丁 0001-Makefile.patch 将顶层 Makefile 替换为 standalone Makefile（CC/AR/RANLIB 变量化、去 -Werror 兼容 clang 15、PREFIX/DESTDIR 安装规则） |
| 2 | lld 链接器缺 libxml2.so.16 | OHOS SDK 的 lld 运行时依赖 libxml2，CI worker 默认 loader 路径找不到 | conanfile.py / test_package 的 build() 注入 SDK llvm lib 目录到 `LD_LIBRARY_PATH`（E120）；库本身是静态 .a 无需链接 |
| 3 | GNU ld 链接的测试程序 exec 被拒 (exit 126) | OHOS 安全机制对部分 ELF 拒绝执行（E046 类） | 改用 lld + LD_LIBRARY_PATH 方案（E120），test_package 二进制可正常执行 |
| 4 | 上游 `make check` 依赖 libcheck | test/testmain.c 直接 `#include <check.h>`，本平台无 libcheck 包 | 探索阶段自定义 standalone test_lwc.c 覆盖核心 API（24/24 PASS）；test_package 以消费者视角调用真实 API（16 断言） |
| 5 | conan-verify G2 首次失败 | `_sdk_llvm_libdir` 误用子键语法 `tools.build:compiler_executables:c`，该 conf 是 dict | 改为整体读取 dict 后取 "c" 键（R33） |
| 6 | CI L0d stub_test_method | test() 仅 `cmake.test()`，无字面 `self.run` | test() 增加 `self.run(bash -c '<binary>', env="conanrun")` 真实执行被测二进制 |

## 源码修改

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| Makefile | NetSurf 构建系统不可用 | 完全替换为独立 Makefile | patches/0001-Makefile.patch（已固化） |

## 依赖版本

- 无运行时依赖
- 编译工具: clang 15.0.4, llvm-ar, llvm-ranlib, GNU make 4.4.1, GNU sed, cmake 4.1.2

## 验证结果

### 探索阶段自定义测试（历史，test_lwc.c）
```bash
$ ./test_lwc
PASS: Created string 'hello' (len=5, data='hello')
PASS: Interning same string returns same pointer (str1==str2)
PASS: Interning different string returns different pointer (str1!=str3)
PASS: lwc_string_isequal(str1,str2) = true
PASS: lwc_string_isequal(str1,str3) = false
PASS: lwc_string_caseless_isequal('hello','HELLO') = true
PASS: lwc_string_hash_value('hello') = 3069866343
PASS: lwc_intern_substring('hello',1,3) = 'ell' (len=3)
=== All tests passed ===
```

### 本轮真实验证（conan create，2026-09-01）
```
1/1 Test #1: test_libwapcaplet ................   Passed    0.03 sec
100% tests passed, 0 tests failed out of 1
libwapcaplet API assertions: 16 passed
```
- 门禁：conan-verify G0-G4 + L2/L4/L5 全 PASS；finish W3 本地 CI 模拟（setup.sh +
  build_and_test.sh）通过，L0（L0a-L0m）全过，无 stub / 无 commands.json 要求（库类型 R38 不适用）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（makefile 模板，静态库，package_info.libs=[wapcaplet]） |
| conandata.yml | github archive URL + sha256 + 补丁声明 |
| test_package/ | CMake 消费者测试（test.c 16 断言，真实调用 API） |
| patches/0001-Makefile.patch | standalone Makefile 替换补丁 |
| libwapcaplet.a | 静态库 (6562 bytes, ELF64 aarch64) |
| libwapcaplet.pc | pkg-config 文件 (version 0.4.3.2) |
| libwapcaplet/libwapcaplet.h | 头文件 |

## 注意事项

- libwapcaplet 是 NetSurf 浏览器组件库，使用 NetSurf 自有的构建系统而非标准 autotools
- 此平台需替换为独立 Makefile 进行编译
- 静态库无需 ELF 签名 / RPATH（.a 不可直接执行）
- lld 的 libxml2.so.16 依赖通过注入 SDK llvm lib 目录到 LD_LIBRARY_PATH 解决（E120），
  而非 GNU ld（GNU ld 链接的二进制在本平台 exec 被安全机制拒绝）
- `clean-verify` 的 G0 阶段始终尝试 `./configure`（框架假设），libwapcaplet 无
  configure 脚本属预期失败，非阻塞（以 conan-verify G2 的 `conan create` 为准）
---

**编译结束**: 2026-09-01 20:03
**最终状态**: published
