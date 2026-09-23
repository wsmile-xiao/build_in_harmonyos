# dictconv 0.2 适配笔记

## 编译环境
- 构建系统: CMake 4.1.2（上游同时带 autotools 与 CMake，实际走 CMake 路径）
- 编译日期: 2026-09-10
- 编译器: clang 17（OHOS SDK 26.0.0.18，/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm）
- 设备: HarmonyOS PC aarch64（真机），profile `ohos-aarch64`
- 工具链: conan 2.29.1，包引用 `dictconv/0.2@ohpcd/stable`
- 状态: built（已完成本地构建与测试，尚未上传制品仓）
- 语言: C++（lang-preflight：task=cpp / detected=cpp，通过）

## 上游与源码
- 上游站点: http://dictconv.sourceforge.net/ （已下线，仅剩归档页）
- 上游版本: 0.2（2007-10 发布，此后无更新）
- 源码: https://ftp.debian.org/debian/pool/main/d/dictconv/dictconv_0.2.orig.tar.gz
  （按 R39 采用权威镜像的 orig tarball，与 ltrace 0.7.3 先例同源）
- SHA256: b3fa22073675973c06db533604aa81272178203a6ee8cb2f86974a7c605ca239
- 许可证: GNU GPL v2 or later（COPYING + 各源文件头部 "either version 2 ... or (at your option) any later version"）
- 语言: C++（同时混少量 C 风格头文件）

## 构建配置
- 构建系统选择: autotools 不可用 —— 2006 年 config.guess 用 `uname -p` 判定 CPU，
  本设备返回 `unknown`，`./configure` rc=1；aclocal.m4 的 AM_PATH_XML2 用 AC_TRY_RUN
  探测 libxml2，交叉编译下不可运行。故改走上游自带的 CMake（`cmake_minimum_required`
  由补丁 0001 补上）
- 依赖: libxml2/2.15.3.1（共享）、zlib/1.3.1.1（静态，R26）
- 依赖定位: 上游 `src/CMakeLists.txt` 用
  `FIND_PATH(XML2_INCLUDE_DIR libxml/xmlreader.h /usr/local/include/libxml2 /usr/include/libxml2)`
  这类硬编码路径；FIND_* 命中同名 cache 变量即直接采用，因此配方 `generate()` 里用
  `tc.cache_variables` 注入 `XML2_INCLUDE_DIR` / `XML2_LIBRARY` / `ZLIB_INCLUDE_DIR` /
  `ZLIB_LIBRARY`，取值来自 `self.dependencies[...].cpp_info`，无需改上游 CMake 脚本
- 无命令行配置项（cache 变量在配方内计算），故 manifest 的 configure_options 为空

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 直接报 `No cmake_minimum_required command is present` | 2007 年 CMakeLists 完全没有该命令，CMake 4.x 视为硬错误 | 补丁 0001 在顶层 CMakeLists.txt 补 `cmake_minimum_required(VERSION 3.5)`；实测 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 三变体（cache/环境/命令行）均失败，变量只对"已声明 <3.5"的工程有效 |
| 2 | `./configure` rc=1，`/usr/bin/uname -p = unknown` | 2006 config.guess + 平台 uname 行为 | 放弃 autotools，改走 CMake；不改上游 config.guess（通用结论见知识 E568） |
| 3 | 编译期 `u_int32_t`/`uint` 报 `bits/alltypes.h: No such file or directory` | musl 头文件不再顺带引入 sys/types.h；上游 7 处头文件依赖 legacy typedef | 补丁 0002/0004-0009 在相关头文件/源文件显式 `#include <sys/types.h>`（曾试全局 `-include sys/types.h`，会污染全部翻译单元，弃用） |
| 4 | 交叉编译找不到 libxml2（FIND_PATH 只查 /usr 路径） | 老式 CMake 依赖探测 | 配方 `generate()` 注入 `XML2_*`/`ZLIB_*` cache 变量（通用结论见知识 E569） |
| 5 | `dictconv --version` / `--help` 不识别 | 上游只用 getopt 登记 -h/-o/-q/-v 短选项；CI L2 冒烟测试用 GNU 长选项 | 补丁 0003 改用 getopt_long，把 `--help/--version/--output` 映射到既有分支（通用结论见知识 E570） |
| 6 | 二进制在无 conanrun 环境下 rc=127（缺 libxml2.so.16） | libxml2 只有共享库制品（仓库内无 shared=False 变体），未链接 RPATH | 运行需 conanrun 提供 libxml2；CI 的 L2 冒烟（直接执行二进制）因此 skip（CI 标注 non-blocking），test_package 内用 VirtualRunEnv 正常验证 |
| 7 | 上游无任何测试套件（autotools 无 TESTS/check_PROGRAMS，CMake 无 add_test/ctest，无 test 目录） | 2007 年小工具 | 消费者测试全部由 test_package/test.sh 提供，并在归档中保留完整的上游测试清点证据 |

## 上游测试
- 上游 TESTS 注册条目: 0
- 上游 CMake 测试: 无（enable_testing/add_test 均无）
- 处理方式: 在本归档中保留上游测试文件、构建目标和 CTest 注册项的完整清点证据
- 全树 grep 依据: `TESTS|check_PROGRAMS|check-local|enable_testing|add_test|ctest` = 0 命中
- 实际复核命令: `find . -type f \( -iname '*test*' -o -iname '*check*' \)` 无测试文件；`cmake --build build --target help` 无 test/check 目标；`ctest --test-dir build --show-only=json-v1` 返回零测试注册项，因此不存在可漏测的上游用例

## 消费者测试（test_package/test.sh，8/8 PASS）
夹具在脚本内生成（FreeDict TEI，根元素 `tei.2`；上游 FreedictReader 硬校验该根节点），
每个用例真实调用包内 `bin/dictconv`，转换结果与期望做字节级 `cmp` 比对；第 8 项额外
确认安装的 OHOS aarch64 ELF 架构并在 conanrun 运行时环境中执行版本查询：

| # | 用例 | 断言 |
|---|------|------|
| 1 | `--version` | rc=0 且含 `Dictconv 0.2` |
| 2 | `--help` | 用法清单含 `.bgl/.tei/.dct/.ifo/.index/.dic` 六个格式标记 |
| 3 | FreeDict(.tei) → PlainText(.dic) | rc=0 且字节一致 |
| 4 | FreeDict(.tei) → StarDict(.ifo/.idx/.dict) | rc=0 且三产物字节一致（含 `--output`） |
| 5 | FreeDict(.tei) → DICT(.index/.dict) | rc=0 且偏移表与词典体字节一致 |
| 6 | 非法输出扩展名 | rc≠0 + `You should specify a valid output file.` |
| 7 | 输入文件不存在 | rc≠0 + `Error converting …` |
| 8 | HarmonyOS/aarch64 消费者运行时 | `readelf` 确认 `Machine: AArch64`，并实际执行 `--version` 返回 0 |

## 验证矩阵（打包二进制实测）
- `bin/dictconv` 240128 字节，sha256 `022aa377129e99daaf762f4beba786c2ad4a65001edb90b7d9caf1c885319711`
- NEEDED: `libxml2.so.16`、`libc++_shared.so`、`libc.so`
- `.tei → .dic` rc=0；`.tei → .ifo/.idx/.dict` rc=0；`.tei → .index/.dict` rc=0
- 同一词典体在 StarDict 与 DICTd 两条输出路径下 md5 一致（`cbe56641f97cd26586d7f8e026560bbe`）
- 输入格式支持: `.bgl/.tei/.dct/.ifo`；输出格式支持: `.dic/.ifo/.index`（源自 dictconv.cpp 扩展名分派，逐行核对）

## 已知上游缺陷（本次未修，超出适配范围）
1. 输出文件名短于 6 字节时 `outfile.compare(outfile.length() - 6, 6, ...)` 无符号下溢，
   抛 `std::out_of_range` 直接 abort（实测 `-o a.dic` rc=134）
2. StarDict 读取路径 `dump()/search()` 返回局部 `std::string` 的 `c_str()`（悬垂指针），
   同一 `.ifo` 输入三次转换得到三个不同 md5 与乱码内容 → 消费者测试只覆盖确定性的
   FreeDict(.tei) 输入路径
3. `.dict` / `.dict.dz`（dictd 明文/压缩词典体）不能作为输入，会以
   `You should specify a valid input file.` 退出（上游设计如此）

## 门禁结果
- `ohc-run.py conan-verify dictconv 0.2`: rc=0，9 项全绿（G0-G4 + L4 checksec + L5 基线）
- W3 本地 CI（`ci/conan/build_and_test.sh archives/d/dictconv/0.2`）: rc=0，
  `Result: 1/1 packages passed (100%), 0 failed`；J01/L0a-L0k/KC/JC/L1e/L4/L5 通过，
  L1 命中白名单 skip，L2 冒烟因共享依赖 skip（CI 标注 non-blocking）
- 详见 `reports/test-report.md`（gitignore，本地保留）

## 标记
- `.conan-verified` / `.build-closed` / `.ci-result.json` / `.staging-verified` 均已生成
- finish **step5b（packaging）** 与 **step8（gen_summary）** 报错：前者是 R19 已废弃的
  旧打包流程（`ohc-run.py package` 已移除，打包由 `conan create` 完成），后者是
  summary 工具 bug（`'str' object has no attribute 'append'`），均不影响归档正确性
---

**编译结束**: 2026-09-11 00:08
**最终状态**: built（本地构建/测试完成，待制品仓发布）
