# isocline 1.1.0 适配笔记

## 编译环境

- 构建系统：cmake（上游自带 CMakeLists.txt，无需覆盖）
- 上游：https://github.com/daanx/isocline，tag v1.1.0（2026-04-21）
- 源码包：https://github.com/daanx/isocline/archive/refs/tags/v1.1.0.tar.gz
- sha256：`1e5f0efa2b719c3e1d292f501e5329e141a039deefc801099f8bbb9a50255531`（直连 GitHub 下载后经 certutil 实测）
- 编译日期：2026-09-17
- 编译器：clang 15（aarch64-linux-ohos，待真机预检实证）
- 状态：built（配方完成，待真机 `conan create` 全部门禁验证）

## 上游测试审计（R51 三步法第 1 步：清点）

- `TEST(`/`TEST_F`（gtest）：0 处
- `def test_`（pytest）：0 处
- `enable_testing` / `add_test` / `include(CTest)`（ctest）：0 处
- `check_PROGRAMS` / `TESTS`（automake）：不适用（CMake 项目），且无 `check`/`test` 构建目标
- 结论：**上游确无自动化测试套件**。`test/` 目录仅含 3 个演示文件：
  - `test/example.c`——交互式 readline 主循环（阻塞读 stdin，需真实 TTY）
  - `test/test_colors.c`——可视化终端色板打印（有 main 但无断言，只输出色板）
  - `test/Example.hs`——Haskell 绑定使用示例
- 因此 `test_package/MANIFEST.yml` 写入 `upstream_tests_exist: false` + 非空 `upstream_test_audit`，
  主配方 `build()` 不调用 `cmake.test()`，`test_package` 以 13 项消费者断言补全覆盖。

## 编译步骤（待真机预检执行）

```bash
conan create archives/i/isocline/1.1.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

预期：`cmake configure`（`IC_BUILD_TESTS=OFF`）→ `build`（静态库 + 共享库双目标）→
`package()` 按 `shared=False` 裁剪 `.so` 产物 → `test_package` ctest 1/1 通过 →
消费者二进制默认模式 12 CHECK-OK + 管道 stdin 模式 1 CHECK-OK。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游恒同时构建静态库与共享库，忽略 `BUILD_SHARED_LIBS` | 上游 CMakeLists 硬编码 `add_library(isocline STATIC …)` + `add_library(isocline_shared SHARED …)` 两个目标 | 不改上游构建（无补丁）：`package()` 按 `shared` 选项删除对侧产物（`*.a` 或 `*.so*`），保证单包单形态；实现见 `conanfile.py::_keep_selected_library_form` |
| 2 | 上游 `IC_BUILD_TESTS` 构建的演示程序无法自动化运行 | `example` 阻塞读 stdin（需 TTY），`test_colors` 仅可视化输出、无断言、无 ctest 接线 | `generate()` 设 `IC_BUILD_TESTS=False`，不构建演示程序；等价的 API 覆盖由 `test_package/test_isocline.c` 提供（含管道 stdin 的 `ic_readline` 端到端内容断言） |
| 3 | 本机无 Python/Conan，无法本地预检 | Windows 执行器环境仅有基础工具链 | 按任务守则由 HMBS 后台执行真机预检；本轮只交付未提交工作树 |

## 源码修改

无补丁（`patches: {}`）。纯 C99 零依赖源码在 OHOS 上无需任何平台适配修改；
`#ifdef __OHOS__` 未引入（R8/PF5 合规）。

## 依赖版本

- 无外部依赖（`requirements()` 为空实现，仅声明无依赖；源码经审计无 pthread/math/dlopen 链接需求）

## 防证伪说明（上游测试三步法第 3 步前置准备）

- 断言均为内容比较（`strcmp` 精确匹配、`==` 数值比较、成员枚举），非空输出比较：
  管道 stdin 用例若 fixture 为空，`ic_readline` 返回 NULL 或空串，`strcmp(line, "hello isocline")==0`
  即失败——空文件比空文件式误报在本套件中不可能通过。
- `ic_readline` 管道行为是上游文档明确承诺的回退路径（dumb terminal / pipe / 重定向时直接读一行），
  非未定义行为；若真机实测该回退不符合预期，预检日志会显示 `CHECK-FAIL: stdin-readline-content`，
  下轮移除该用例并在 PR 补充说明中如实扣减通过率。

## 验证结果

- 待 HMBS 真机预检回填（`conan create` 日志中的 ctest 输出与两行 JSON 机器证据标记）。

## 交付物

无打包产物（纯库配方，`conan create` 生成制品）。

## 注意事项

- `isocline.pc.in` 与共享库 `VERSION` 属性内硬编码的 `1.0.9` 为上游版本号疏漏（1.1.0 发布时未同步），
  仅影响 pkg-config 描述字段与 `.so` soname，不影响功能；未打补丁（保持与上游一致，待上游修复）。
- 默认 `shared=False`：OHOS 系统目录无 `libisocline` 同名库（R26 不适用），静态为默认形态；
  `shared=True` 同样受支持（保留 `.so`、删除 `.a`）。

---

**首轮工作树完成**：2026-09-17
**最终状态**：built（待真机验证）
