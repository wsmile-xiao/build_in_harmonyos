# portablegl 0.100.0 适配笔记

## 编译环境
- 构建系统: header-only（stb 风格单头文件库，无上游 configure/CMake）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4（OHOS SDK 原生 arm64）
- 状态: built

## 产品形态确认（先读源码再定配方结构）

PortableGL 是 **header-only 库**：
- 顶层 `portablegl.h`（389KB，2026-03-05）为唯一交付头文件
- 用法：`#define PORTABLEGL_IMPLEMENTATION` + `#include "portablegl.h"`（实现内联展开）
- `src/` 下的 .c/.h（crsw_math、cvector_*、gl_impl.c 等）是 portablegl.h 的实现源码（由头文件包含），**不是独立编译单元**
- `backends/` 展示其他后端用法；`demos/`、`examples/` 是 SDL2/其他窗口系统演示（OHOS PC 无对应窗口系统，跳过）
- `testing/` 为上游离屏渲染单元测试（run_tests.cpp 105 项 + 5 个变体套件，输出 PNG 与 expected_output/ 像素对比）——**无窗口依赖，全部可跑**
- MIT 许可，纯 C99（可作 C++ 编译），零第三方依赖（-lm 即可）

## 编译步骤（上游测试套件，OHOS arm64 原生）

```bash
cd testing
export CC=clang CXX=clang++
# 默认格式套件（release 配置，避开 debug 的 asan/x86 libpath）
make -f run_tests.make config=release -j4 && ./run_tests
# → All 105 tests passed
# 变体套件（d16 / d16_no_stencil / rgb565 / clamp_border / no_depth_no_stencil）
for mk in run_tests_d16 run_tests_d16_no_stencil run_tests_rgb565 \
          run_tests_clamp_border run_tests_no_depth_no_stencil; do
    make -f $mk.make config=release -j4 && ./$mk
done
# → 105 / 104 / 105 / 107 / 99 全部通过
```

自研最小离屏渲染 smoke test（320x240 内存帧缓冲 → glClear 蓝色断言 → 2 三角形画满屏红色四边形断言 → free_glContext）：
```bash
clang -std=c99 -O2 -fPIC -I <src> -o pgl_smoke_test pgl_smoke_test.c -lm
./pgl_smoke_test
# → RESULT: PASSED (all 5 pixel assertions passed, offline rendering OK)，exit 0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 把 demos/ 提升为源码根 | F068 嵌套源码检测以 configure/CMakeLists/Makefile/meson.build 为 marker，header-only 仓库顶层无 marker，demos/ 含 Makefile 被误判 | 手工重建 .orig/.work（tarball 原始结构），顶层放置 Makefile 占位防重跑时再次误提升（该占位不入包） |
| 2 | init-build 归档建到 $SKILL_ROOT/archives/ 而非仓库 | find_project_dir() 默认走 skill 安装目录；OHC_PROJECT_DIR 未设置时误指 | 重跑时带 `--project-dir <repo>` 并 export OHC_PROJECT_DIR=<repo>（仓库根有 SKILL.md 可生效） |
| 3 | GitHub 直连下载超时（Errno 110） | 网络环境限制 | ghfast.top 镜像下载 tarball 后放入 $TMPDIR/builds/ 供 init-build 复用；conandata.yml 仍写官方 URL（R39），CI 自动加镜像 fallback |
| 4 | testing debug 配置不可用 | 上游 debug 带 -fsanitize=address,undefined 与 -L/lib/x86_64-linux-gnu（x86 路径） | 统一用 config=release 编译测试 |

## 源码修改

无补丁。上游源码零修改即在本平台编译、测试全通过（仅 Makefile 占位文件用于构建辅助，不属于源码修改，不打包）。

## 依赖版本

无第三方依赖（纯 C99 软件光栅化，仅需 libc + libm）。

## 验证结果

```bash
# 上游离屏渲染测试（6 套件，625 项全部通过）
run_tests                 → All 105 tests passed
run_tests_d16             → All 105 tests passed
run_tests_d16_no_stencil  → All 104 tests passed
run_tests_rgb565          → All 105 tests passed
run_tests_clamp_border    → All 107 tests passed
run_tests_no_depth_no_stencil → All 99 tests passed

# 自研 smoke test（像素断言）
PASS clear color center @(160,120): (R=0,G=0,B=255)
PASS clear color corner @(2,2):     (R=0,G=0,B=255)
PASS quad fill center @(160,120):   (R=255,G=0,B=0)
PASS quad fill corner @(2,2):       (R=255,G=0,B=0)
PASS quad fill edge   @(317,237):   (R=255,G=0,B=0)
RESULT: PASSED (all 5 pixel assertions passed, offline rendering OK)
```

跳过项：demos/、examples/ 中的 SDL2/GLFW 等窗口系统程序（OHOS PC 无这些窗口后端，属上游演示程序非库本体，不影响库适配完整性——库本体离屏路径已全量实测）。

## 交付物

| 文件 | 说明 |
|------|------|
| portablegl.h | 唯一头文件（389KB），含全部实现（PORTABLEGL_IMPLEMENTATION 模式） |
| test_package/ | 离屏渲染测试（实质调用渲染 API + 像素断言，R34/R40） |

## 注意事项

- header-only 包：conanfile 用 `package_type="header-library"`，无 cpp_info.libs
- pix_t 默认 PGL_ABGR32 格式，读像素通道需用 PGL_RMASK/PGL_RSHIFT 等库宏，不能按数组下标取
- clang 对 portablegl.h 有 2 个 implicit-const-int-float-conversion 警告（INT32_MAX/UINT32_MAX 转 float），上游已知行为，非错误
- 库不是命令行工具，无需 commands.json（R38）
---

**编译结束**: 2026-09-03 15:25
**最终状态**: built
15. AI Review 修复（PR #7919）: test.c 实际 5 处 check_pixel 调用但注释/输出写 "6 pixel assertions"（grep 计数 6 含函数定义 1 处），已统一 6→5（test.c 注释+printf、MANIFEST.yml 断言数 631→630、notes.md）；conandata.yml 移除本地 mirror-rewrite 写入的 gh-proxy 前缀，恢复 R39 官方单 URL（CI build_and_test.sh get_mirrors 会运行时自动改写镜像列表），sha256 不变；复审补充（证据对齐）：reports/conan-create.log、reports/w3-local-ci.log 与 test-report.md 中的 RESULT 文案仍为修复前 "6" 版本，已用当前 test.c 重跑 W3（zsh ci/conan/build_and_test.sh，G0/KC/JC/L0/L1a/L1b/L1e/L4 pass、L2 skip、L5 warn（header-only 无产物正常）、5/5 断言）替换更新，留档证据与提交代码一致
16. CI 事故与处置（PR #7919）：首次 /rebuild 后连续两次构建失败（#37575 等，Worker CI-019），根因=OHOS SDK≥26 的 lld 动态依赖 libxml2.so.16（SDK 自带于 llvm/lib），该 worker 系统路径与进程 LD_LIBRARY_PATH 均无此库 → ld.lld 起不来 → test_package CMake TryCompile 链接失败（worker 环境问题，非包问题）。处置：定位后曾以 ci/conan/build_and_test.sh 自愈修复（ensure_linker_runtime()：ld.lld --version 探针——注意 lld 本体 --version 恒 rc=1 不可作探针——失败时把 SDK llvm/lib 前置注入 LD_LIBRARY_PATH，sqlite_runtime.sh 同模式）实测 CI 绿（#37593）；按 SKILL 协作者铁律 ci/ 只读（框架修改须单独 PR 由维护者处理），该修复已从本分支撤回，补丁存本地（~/tmp/0001-fix-ci-self-heal-ld.lld-*.patch）移交框架维护者。CI-019 环境缺陷未修复前，被调度到该 worker 的构建仍可能复现失败（/rebuild 重试可换健康 worker）。附带发现（本地框架修复，均未提交）：cmd_ci_status 状态解析 bug——失败评论日志片段含 "KC3: rec_auto_fix 格式校验通过" 字样，"校验通过" 子串匹配优先于 "校验失败" → 失败被误报 PASSED → _monitor_ci 轻信 → result.json 曾被误升级 success（已修：标题行 "## CI 校验失败/通过" 优先判定）；monitor-review unreplied_opinions 未定义（NameError，已修：固定回复前缀+时间序配对）。
