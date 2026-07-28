# slang 2.3.3 适配笔记

## 编译环境
- 构建系统: autotools（自定义 configure 脚本）
- 编译日期: 2026-07-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: `curl -fsSL -o slang-2.3.3.tar.bz2 https://www.jedsoft.org/releases/slang/slang-2.3.3.tar.bz2`
2. 解压源码到工作目录
3. 运行 configure:
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX
   ```
4. 编译: `make -j1`
5. 安装: `make install DESTDIR=$TEST_PREFIX`
6. 测试: `make -j1 check`，并额外编译、执行上游 `utf8/test_isxxx.c`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoconf/config.guess: unable to guess system type` | config.guess(2016-04-02) 不识别 HarmonyOS(uname -s) | 在 conanfile.py build() 中 patch config.guess/config.sub 添加 HarmonyOS/OHOS 支持（E007/E160） |
| 2 | `C compiler cannot create executables` | OHOS 上 clang 需要 --target 标志才能找到 CRT 文件 | 在 generate() 中添加 --target=aarch64-unknown-linux-ohos 到 CFLAGS（E001） |
| 3 | 测试结果固定报告 94，与清单和实际 Makefile 不一致 | 配方将旧的估算数硬编码为执行数 | 从配置后生成的 Makefile 动态统计 src/module/slsh 测试，并单独计入 `utf8/test_isxxx.c` |

## 源码修改

本次适配在 conanfile.py build() 中 inline-patch autoconf/config.guess 和 autoconf/config.sub 以识别 HarmonyOS（E007/E160/E072）；在 generate() 中添加 --target=aarch64-unknown-linux-ohos 到 CFLAGS（E001）。测试阶段执行完整 `make -j1 check`，并补充执行上游未挂入该目标的 `utf8/test_isxxx.c`。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| 无外部依赖 | - | libm/libdl/libpthread 由系统提供 |

## 验证结果

### make check 输出
2026-07-27 真机预检确认当前提交可以完成编译，`make -j1 check` 返回成功。旧配方曾固定报告 94/94；复核上游 Makefile 后已移除该硬编码：src harness 为 97 个 case，模块测试由 configure 动态选择，slsh 为 11 个脚本，并额外执行 1 个 `utf8/test_isxxx.c`。当前 OHOS 配置预期共 125 个 case，下一轮预检将由配方按生成的 Makefile动态报告实际数量。

### conan-verify 结果
2026-07-27 在 `ohos@c1.sermc.net` 完成真机预检：配方编译通过，`test_package` 的 `./test_slang` 通过，`make -j1 check` 通过。修正测试统计及补入 `test_isxxx` 后需要完整复跑，以更新最终测试数。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libslang.so | 共享库 |
| lib/libslang.a | 静态库 |
| include/slang/slang.h | 主头文件 |
| bin/slsh | S-Lang shell 解释器 |

## 注意事项

- slang 编译不依赖外部第三方库，系统自带 libm/libdl/libpthread 即可
- 该软件为 C 语言项目，C++ 编译器可选用于构建模块
- 测试统计以配置后生成的 Makefile 为准，不再使用旧的 67/94 固定值
- `utf8/test_isxxx.c` 不属于上游顶层 `make check`，因此由 Conan 配方显式执行

---

**编译结束**: 2026-07-27
**最终状态**: built（测试统计修正后待再次完整真机预检）
