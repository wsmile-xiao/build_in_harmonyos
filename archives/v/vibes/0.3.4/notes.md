# vibes 0.3.4 适配笔记

## 编译环境
- 构建系统: custom（client-api/C++ 无上游构建系统，配方直接编译 `src/vibes.cpp` 生成 `libvibes`）
- 编译日期: 2026-09-19
- 编译器: clang/clang++（aarch64-linux-ohos，OHOS 原生）
- 状态: built（待真机预检 / HMBS rule4 门禁）

## 适配范围
本配方打包 **VIBES C++ client API**（`client-api/C++`）：单翻译单元 `vibes.cpp` + 头文件 `vibes.h`，下游使用者链接 `libvibes` 向其查看器发送 JSON 绘图命令。上游的 `viewer/` 是 Qt5/Qt6 GUI 桌面应用，需真实显示器且 Qt GUI/SVG 组件在 OHOS headless 环境不可构建，属于非本配方打包范围。

## 编译步骤
1. `get()` 下载官方 tag 源码包并解压（`strip_root=True` → `VIBES-0.3.4`）
2. `generate()`：从 `tools.build:compiler_executables` 解析 C/C++ 编译器与归档器（llvm-ar/ar），注入可写 TMPDIR
3. `build()`：
   - `clang++ -std=c++11 [-fPIC] -c client-api/C++/src/vibes.cpp -o vibes.o`
   - 静态：`llvm-ar rcs libvibes.a vibes.o` + `ranlib`；共享：`clang++ -shared vibes.o -o libvibes.so`
4. `package()`：安装 `vibes.h` → include/、`libvibes.*` → lib/、`COPYING`+`COPYING.LESSER` → licenses/
5. 上游无自动化测试 → `build()` 输出 `HMBS_UPSTREAM_TEST_RESULT` 为 `status=no_tests`（真实审计见 test_package/MANIFEST.yml）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | client-api/C++ 无构建系统 | 上游客户端库只提供 vibes.h+vibes.cpp，靠使用者引入编译 | 配方直接调 clang++ 编译单翻译单元，静态/共享按 `shared` 选项生成 |
| 2 | 绘图需连接查看器？ | 查看器是独立进程监听 JSON 文件，客户端库把命令写入文件 | test_package 用 `beginDrawing(file)` 文件模式 headless 自测，读文件校验 JSON 输出，无需 GUI |
| 3 | 编译器须从 Conan conf 取（R33） | 裸用 `${CXX}` 在 release worker 上为空 | 从 `tools.build:compiler_executables` 解析，缺路径时 PATH 回退 |
| 4 | 无上游测试 | client-api 仅有 examples 演示程序（VIBES_TEST 宏只打印 DONE，无断言）；viewer/tests 是 Qt fixture | 如实声明 `upstream_tests_exist:false` + 审计，test_package 以 13 项真实 API 断言补全 |
| 5 | 端到端绘图自测的确定性 | 库在每次 fputs 后 fflush | 测试从另一句柄读已冲刷文件内容校验负载 |

## 源码修改
无补丁（`patches/` 不创建）。纯 C++11 客户端库零外部依赖，无需 OHOS 适配修改。

## 依赖版本
无（仅 STL + stdio，零外部依赖）。

## 验证结果
- 上游测试：无自动化套件（审计见 test_package/MANIFEST.yml `upstream_test_audit`），`HMBS_UPSTREAM_TEST_RESULT` 输出 `no_tests`（0/0）
- 新增消费者测试：test_package `test_vibes.cpp` 13 项断言（JSON 序列化 + 文件模式绘图端到端），`HMBS_TEST_PACKAGE_RESULT` 据真实 CHECK-OK 计数
- 真机预检（HarmonyOS aarch64）由 HMBS 后台执行，此处在工作树阶段如实标注待验证

## 注意事项
- 下游如需真实图形渲染，须自行另跑 VIBES 查看器（Qt GUI，非本配方产物）
- 库文件写入容忍相对路径；测试从可写 cwd 运行
- `beginDrawing(fileName)` 以追加模式打开；测试用新文件避免残留

## 本轮修复（CI L0d stub_test_method）
- 现象：CI 质量门 L0d 报 "test() method has no self.run() call — likely a stub"，拦截 conan-build-test。
- 根因：test_package/conanfile.py 的 test() 用 `subprocess.run()` 直接执行被测程序，未调用 Conan 原生 `self.run()`；CI `grep -q "self\.run"` 与 preflight PF3 的 AST 检查都要求 `self.run`/`self.run_command`。
- 修复：把 test() 内实际执行改为 `self.run('"<bin>" > <log> 2>&1', cwd=run_dir)`，stdout 重定向到确定日志文件作唯一计数源，再读日志统计 CHECK-OK/CHECK-FAIL（无 stdout 算术），rc 直接来自 self.run。测试逻辑/断言数（13）不变。
- 验证：python3 ast 解析通过；CI grep 命中 `self.run`；preflight `check_test_substance` 返回 PASS。
