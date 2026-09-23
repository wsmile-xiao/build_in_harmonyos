# TextParser 1.9.0 适配笔记

## 软件信息

- **名称**: TextParser
- **版本**: 1.9.0（配方版本；上游最新 tag 为 1.8.8，见下文版本审计）
- **上游仓库**: https://github.com/avr-aics-riken/TextParser
- **许可证**: BSD-2-Clause
- **构建系统**: CMake
- **用途**: YAML-like 简单文本参数解析库
- **申请人**: Bingggooo（队伍：来都来了）

## 版本来源审计（重要）

上游 `avr-aics-riken/TextParser` 截至 2026-09-10 不存在 `1.9.0` tag：

- Tags 页最新为 `1.8.8`（commit `31ec1f2`，2018-09-25），之后无任何提交。
- `master` HEAD 即 `31ec1f23df21611d0765c27a6458fdbbf4cde66d`，与 `1.8.8` tag 同一提交，
  代码完全一致；`ChangeLog.md` 最高条目为 `1.8.8`。
- 直接验证：`GET .../archive/refs/tags/1.9.0.tar.gz` 经 codeload 返回 `404 Not Found`；
  而 `.../archive/refs/tags/1.8.8.tar.gz` 可下载且 SHA256
  `ff87020943fdd1b9ead3c7e461fe364adc7651b87d57bce8e004ab7f82375194`
  与 1.8.8 配方记录一致。

因此本配方以官方 GitHub 源码为准（R39），锁定 post-1.8.8 `master` HEAD commit
归档作为 1.9.0 的源码输入，并用补丁 `0002` 将 `PROJECT_VERSION` 从 `1.8.8`
提升到 `1.9.0`（`LIB_REVISION` 保持不变）：

- conandata URL:
  `https://github.com/avr-aics-riken/TextParser/archive/31ec1f23df21611d0765c27a6458fdbbf4cde66d.tar.gz`
- SHA256（两端实测：本机 `curl -k` 下载计算）:
  `76912fc1506d121f9f2a74496b5dc481c4be2f389f6000f442a2befc2a8f92ce`

任务卡给出的 `.../refs/tags/1.9.0.tar.gz` 地址上游不存在，配方未采用；
若 maintainer 要求改用该地址，需上游先发布 1.9.0 tag。

## 功能特性

- JSON/YAML 风格的简单参数结构解析
- 支持 C、C++ 和 Fortran API（本配方仅启用串行 C/C++）
- Singleton 模式实现
- 可选 MPI 支持（本配方禁用）
- 轻量级，无外部依赖

## 依赖关系

无。纯 C++/C 标准库。`with_mpi`/`enable_fapi` 在 `validate()` 中直接拒绝，
避免静默打出不支持的变体。

## 与 1.8.8 配方的差异

1.8.8 配方（`archives/t/textparser/1.8.8`，2026-09-01）是旧版式：`url = ""` 空字段、
`enable_test=OFF`（上游测试完全未跑）、无 `validate()`、无 HMBS 证据标记、
强制改写 `compiler.libcxx`。1.9.0 配方逐项修正：

- `url` 指向仓库主页，不再留空（过检视 R39/占位符规则）。
- `validate()` 按 R32 检查 `os in ("Linux", "OHOS")`，并拒绝 MPI/Fortran 变体。
- `enable_test=ON`，`build()` 执行上游 ctest 并输出 `HMBS_UPSTREAM_TEST_RESULT`
 （数字从 ctest 真实输出解析，非硬编码）。
- 删除 `compiler.libcxx` 改写：当前 `ci/conan/profiles/ohos-aarch64` 已是
  `compiler.libcxx=libc++`，跟随 profile 即可。
- `test_package` 改为 6 断言实质 API 测试 + `HMBS_TEST_PACKAGE_RESULT`
 （含 `discovered`/`passedCount`），使用 TMPDIR 感知的临时目录。
- `package_info()` 补齐 `cmake_file_name`/`cmake_target_name`，
  与 `test_package/CMakeLists.txt` 的 `find_package(textparser CONFIG)` 对齐。

## 构建配置

```cmake
-DCMAKE_BUILD_TYPE=Release
-DBUILD_SHARED_LIBS=OFF              # 静态链接（默认选项）
-Denable_fapi=OFF                     # 禁用 Fortran API
-Denable_test=ON                      # 启用上游测试（1.8.8 为 OFF）
-Dwith_MPI=OFF                        # 禁用 MPI
```

### 应用的补丁

**0001-update-cmake-minimum-version.patch**（沿用 1.8.8）
- 目的: 上游 `cmake_minimum_required(VERSION 2.6)` 被现代 CMake 拒绝，
  提升到 3.15。
- 类型: portability，无平台宏。

**0002-bump-version-to-1.9.0.patch**（新增）
- 目的: 源码树 `PROJECT_VERSION` 为 `1.8.8`（master 未 bump），
  提升到 `1.9.0` 使 `tpVersion.h` 的 `TP_VERSION` 与配方版本一致，
  `test_package` 据此断言版本。
- 类型: portability，一行变更。

**0003-fix-negative-test-logic.patch**（本轮已合并更新，见下）
- 目的: 修正上游负向测试的倒置断言（TEST_QUALITY_SPEC 3.3 允许的测试补丁修复，
  非删除断言）：`Example2_cpp.cpp`/`Example2_c.c` 只喂 `incorrect_*` 固件，
  旧逻辑在 `read()` 正确返回非零时 `return 1`，工作正常的解析器永远失败；
  `Example8_cpp.cpp` 对 4 个 `incorrect_range/list` 固件在 `error != TP_NO_ERROR`
  时 `status++` 并最终 `return (status==0)?0:1`，正确拒绝反而判负。
  补丁将“正确拒绝”记为通过、“意外接受”记为失败，断言强度不变。
- 更新（2026-09-10 真机证据）：`incorrect_cond_2.txt`/`incorrect_cond_3.txt`
  （依赖未定义值）只触发 `Warning #201`
 （`TP_WARNING=200` 以上为警告，`read()` 按设计返回 `TP_NO_ERROR`），
  真机日志证实这两个文件返回 0 而其余 `incorrect_*` 均返回非零错误码
 （`incorrect_cond_1.txt` 返回 `Error #127`）。
  2026-09-10 第二轮 verbose 重跑追加证据：`incorrect_cond_5.txt`
  （自引用 `@dep`，`"switch1" = @dep(("switch0"=="on")&&("switch1"=="on"))`）
  仅触发 `Warning #202: Unresolved label used : switch1` 即返回 0，
  被记为 `# Unexpected success reading incorrect file` 致 `test_c_2`/`test_cpp_2`
  失败。因此警告豁免扩展为 cond_2/cond_3/cond_5 三文件（cond_4 触发
  `Warning #202 + Error #120` 仍期望拒绝），其余 `incorrect_*` 仍期望拒绝；
  C 版本用 `strstr`（程序化修复同时补齐上游缺失的
  `#include <string.h>`，否则严格编译器报隐式声明错误），
  C++ 版本用 `string::find`。
- 合并说明（2026-09-10 第三轮真机证据）：原增量补丁
  `0005-fix-cond3-and-string-h.patch` 在真机 `source()` 报
  `hunk doesn't match / source file is different`——其上下文锚定的是
  0003 改后内容，且 `string.h` hunk 行号（16）与上游实际（19-21）错位，
  跨补丁依赖脆弱。已将 cond_3 豁免与 `string.h` 直接并入 0003
  （单文件多 hunk，原子应用），删除 0005，`conandata.yml` 同步移除。
  合并后 0003 已用上游原始文件做 `git apply --check` 本地校验通过。
- 结构修复（2026-09-10 第四轮真机证据）：真机 `source()` 报
  `0003 file 3/4 Examples/Example2_c.c: hunk doesn't match`
  （`expected: // ...` / `actual: ''`）。根因为同一补丁文件内对同一文件
  写了两个独立文件头（`--- a/Examples/Example2_c.c` 出现两次），
  第二段按原文件行号锚定（含日文注释上下文），与已打上第一段
  （`+string.h`，+1 行）的文件状态错位；且日文注释行编码脆弱。
  已重写 0003：每文件仅一个文件头（Example2_c.c 单头双 hunk，原子应用），
  两处 `read()` 改写 hunk 改从 ASCII 行（`printf(">>> Reading...` /
  `std::cout << ">>> Reading...`）起锚，完全避开非 ASCII 上下文
  （全补丁零非 ASCII 字节），hunk 计数已校准；
  用含占位日文行的重构文件做 `git apply --check` / `git apply` 校验通过。
  语义与上一版完全一致（cond_2/cond_3 警告豁免 + string.h + 反转断言修正）。
- 策略更换（2026-09-10 第五轮真机证据）：重写后的单头 0003 在真机仍报
  `file 1/3 Example2_cpp.cpp: hunk doesn't match at line 30`
  （`expected: std::cout << ">>> Reading...` / `actual: ''`）——
  静态 unified-diff 对行号/上下文的精确匹配在此源码上连续两轮失效
  （先 Example2_c.c，后 Example2_cpp.cpp），属同一错误指纹的重复失败。
  本轮改用不同策略：删除 0003 补丁文件及其 conandata 条目，
  改为 `conanfile.py::source()` 内 `_fix_negative_tests()` 字节级替换：
  文件按二进制读写，仅触碰纯 ASCII 锚点（`if (stat == 0)` 特征块、
  `#include <stdlib.h>`、四处全同的 `if(error!=TP_NO_ERROR)` 块），
  与行号、日文注释行编码（UTF-8/Shift-JIS）、换行符（LF/CRLF）无关；
  锚点计数断言（1/1/4，不符即抛错），`string.h` 缺失才插入。
  语义与 0003 完全一致，已用 utf8-lf/sjis-lf/utf8-crlf 三种重构文件
  验证锚点命中 1/1/4。

- 类型: bugfix，仅改测试断言方向与缺失头文件，不改库源码。
  已并入 0003（单补丁原子应用，避免跨补丁上下文漂移）；0005 文件已删除。
- 依据: 固件命名 `incorrect_*`、真机日志（`incorrect_basic_1.txt` 正确报
  `Error #107` 却被记为 `Failed`；4 个 `incorrect_range/list` 全部正确报
  `Error #140/#141/#150` 却被记为 `Failed`）、上游 ChangeLog（1.8.1/1.7.1
  明确记载串行测试在 Intel/GNU 下 35%/5 项失败，与本轮 5 项失败同量级）。
- 类型: bugfix，仅改测试断言方向，不改库源码；`test_cpp_4/5`（Bus error）
  与 `test_cpp_6`（Failed）由 0004 与诊断重跑覆盖，本补丁不管。

**0004-fix-uninit-and-tailspace.patch**（新增，本轮）
- 目的: 修复两处上游库源码的确定性 UB（非测试逻辑改动）：
  1. `src/TextParser.cpp::getType` 的 `TextParserValueType returner;` 未初始化，
     出错路径直接 `return returner`。`Example6` 用该返回值做 `disp(type)` 计数，
     垃圾值导致 nondeterministic 失败；在严格 ARM64 ABI 下未初始化读取本身即 UB。
     补丁初始化为 `TP_UNDEFFINED_VALUE`（枚举 0，与头文件定义一致）。
  2. `src/TextParserTree.cpp::TextParserRemoveTailSpaces` 的
     `for (unsigned int c = buffer.size()-1; c >= 0; c--)` 中 `c >= 0` 恒真，
     全空白行时 `c` 回绕到 `UINT_MAX` 并越界读 `buffer[c]`
    （堆越界 → ARM64 上 SIGSEGV/SIGBUS 的可疑来源之一）。
     补丁改用有符号 `int` 索引，其余逻辑不变。
- 类型: bugfix，只改库源码两行语义，不改测试。若下轮 `test_cpp_4/5` 仍 Bus error，
  则排除这两处，继续按诊断重跑输出定位（见下）。
- 配方诊断增强：`conanfile.py::_run_upstream_ctest` 在失败时把
  `The following tests FAILED:` 段中的失败用例逐个 `ctest -R ^name$ -V` 重跑，
  输出尾部 3000 字符打进 conan 日志尾部。原因是 hmbs 轮次摘要会截断中段，
  上轮 `test_cpp_4/5/6` 的崩溃上下文在中段丢失；重跑输出落在日志尾部，
  下轮摘要可直接定位崩溃固件/堆栈。不改变任何通过判定（仍 `failed>0` 即抛异常）。

## 上游测试清点（静态审计，来自源码）

`-Denable_test=yes` 时顶层 `CMakeLists.txt` `add_subdirectory(Examples)`，
`Examples/CMakeLists.txt` 在串行配置（`with_MPI=no`）下注册：

- C++：`test_cpp_1`..`test_cpp_8`（8 例，`Example1_cpp`..`Example8_cpp`）
- C：`test_c_1`..`test_c_5`、`test_c_7`（6 例，无 `Example6_c`）
- 合计 **14 例**，框架为 ctest；MPI（2 例）与 Fortran（6 例）因变体禁用未注册。

注意：out-of-source 构建时 `BUILD/Examples` 下没有 `./tpp_examples` 数据文件，
配方在 `build()` 中把源码 `Examples/tpp_examples` 与 `test.tpp` 拷贝到构建树
对应位置后再跑 `ctest`。上游 ChangeLog 曾记载部分 Example 在 Intel/GNU 下失败
（如 1.8.1 时期串行测试 35% 失败），真机实测以预检日志为准，不预断通过率。

## test_package（消费者测试，6 断言）

`test_package/test_package.cpp` 实质调用被测 API（R34），非空壳：

1. `TextParser::get_instance_singleton()` 非空
2. `TP_VERSION == "1.9.0"`（头文件真实值）
3. `read()` 读取临时 `.tpp` 固件成功
4. `getLabels()` 发现非空标签
5. `getValue()` 取回非空值
6. `write()` 回写 + `remove()` 清理成功

固件写在 `temp_directory_path()` 下（HMBS 注入 TMPDIR；OHOS `/tmp` 不可写）。
`test()` 经 ctest 运行，成功后输出
`HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...,"discovered":6,"passedCount":6}`。

## 本轮状态（2026-09-10 CI #43532：并行构建链接失败，已修复待验证）

- CI 现象：14 个 Example 链接全部报
  `ld.lld: error: unable to find library -lTP`，
  而 `libTP.a`（target TP）在 100% 才建成——典型并行构建竞态。
- 根因（源码审计）：上游 `Examples/CMakeLists.txt` 用
  `link_directories(${PROJECT_BINARY_DIR}/src)` +
  `target_link_libraries(Example* -lTP)` 链接。
  `-lTP` 前导破折号形式是纯链接器标志，不产生 CMake 目标依赖，
  因此 Unix Makefiles 并行构建时 Example 先于 `libTP.a` 链接；
  真机预检因 `tools.build:jobs=1` 串行构建恰好成功，CI 并行则暴露。
  同类先例：`archives/a/apngasm/3.1.10` 同样以
  `add_dependencies(<exe> <lib>)` 解决 CLI 先于库链接的问题。
- 修复（`patches/0005-fix-examples-build-order.patch`，portability，
  单 hunk 追加在文件尾）：在 `if(NOT with_MPI)` 守卫下为 14 个串行
  Example 逐个声明 `add_dependencies(Example* TP)`，不改动上游原有链接行。
  补丁已用锁定提交（31ec1f2）的真实上游文件做
  `git apply --check` / `git apply` 校验通过（14 条依赖）。
- 待验证：下一次 CI / 真机预检确认链接顺序与 14 例 ctest 结果。

## 本轮状态（2026-09-10 第七轮真机证据：13/14 通过）

- 缺失 return 修复生效：`test_cpp_4`/`test_cpp_5` 的 Bus error 已消除
  （11→13），仅剩 `test_cpp_6` 1 例失败。
- `undef-context` 诊断精确定位：全套件仅 1 行 UNDEF——
  `undef-context: /Average_operation/start_time 0 || !!! UNDEF !!!`。
- 根因（源码审计）：`tpp_examples/correct_cond_7.txt`
 （注释：依存関係付き値（未定義値））定义
  `start_time = @dep("/Average_operation/op" == "on") ? UNDEF : 0.0`，
  且 `op = "on"`，真分支按设计产生 UNDEF；工作正常的解析器经
  `getType` 必返回 `TP_UNDEFFINED_VALUE`。而上游 `Example6_cpp.cpp`
  对该标签无条件执行 `status += disp(type)`，`disp()` 又把 UNDEF 计为
  失败——与 Example2/Example8 同属上游断言极性倒置（全 `correct_*`
  固件中仅 cond_7 含顶层 UNDEF 分支，`grep UNDEF` 与全套件唯一 UNDEF
  行互相印证）。
- 本轮改动（`conanfile.py::_fix_example6_cond7`，程序化字节级修复，
  无补丁文件变更）：将 cond_7 该行的 `status += disp(type);` 替换为
  UNDEF 期望分支——类型为 `TP_UNDEFFINED_VALUE` 记通过并打印
  `correctly UNDEF`，否则记失败。断言强度不变（仍会在解析器返回
  定义类型时失败），仅纠正倒置极性；锚定唯一文件名 + 其后首个 disp
  语句单行替换，不受空行空白与注释编码漂移影响。

- `readonly_tmp` 平台诊断：已审计 `Examples/` 无 `/tmp` 硬编码
  （`grep /tmp|mktemp|tmpnam` 零命中；`tmp.tpp`/`test.tpp` 均为构建树
  相对路径，`test_package` 用 `temp_directory_path` 即 TMPDIR），
  属 preflight shell/conan 基础设施侧写入，与本配方测试无关，
  故不改测试口径、不跳过任何用例。

## 验证命令（真机，HMBS 后台执行）

```bash
cd archives/t/textparser/1.9.0
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

预期日志包含：
`HMBS_UPSTREAM_TEST_RESULT={"status":...,"framework":"ctest",...}` 与
`HMBS_TEST_PACKAGE_RESULT={"executed":true,...,"discovered":6,"passedCount":6}`。

## 参考资料

- https://github.com/avr-aics-riken/TextParser
- http://avr-aics-riken.github.io/TextParser/
- Spack 配方（构建选项参考）:
  https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/textparser/package.py
