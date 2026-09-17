# Test Report — pangomm 2.56.2

- 日期: 2026-09-14
- 平台: HarmonyOS PC (aarch64, musl, clang 15, target `aarch64-linux-ohos`)
- 构建系统: Meson (min 0.62.0; 本机 meson 1.11.1) + conan (profile ci/conan/profiles/ohos-aarch64)
- 任务: Pango 的 C++ 绑定（pangomm-2.48 API），pangomm/2.56.2 端到端验证

## 上游测试

pangomm 2.56.2 **无任何可执行的上游测试**（非静默跳过，证据三重）：

1. 全部 meson.build（根 / `pango/` / `pango/pangomm/` / `tools/extra_defs_gen/` / `docs/reference/`）grep `test(` 零注册；
2. `meson_options.txt` 无 `build-tests` 选项（选项全集：maintainer-mode / warnings / dist-warnings / build-deprecated-api / build-documentation / msvc14x-parallel-installable）；
3. `tests/` 仅含 autotools `Makefile.am` 且 `SUBDIRS =`（空壳），无 meson.build 入口 → `meson test` 无事可做。

与 2.50.1 结论一致（上游测试体系自始由 meson 承载且未注册，不存在因 HarmonyOS 限制被跳过的测试）。

## test_package（消费者视角 L1 验证）

编译 + 链接 + 运行全通过。

- 编译: `clang++ test.cpp -o test_probe`（-I/-L 全部来自 conan 依赖 cpp_info，无宿主机头文件）
- 链接: `-lpangomm-2.48 -lcairomm-1.16 -lglibmm-2.68 -lgiomm-2.68 -lsigc-3.0`
- 运行: `LD_LIBRARY_PATH=<全部依赖 lib 目录 + SDK libc++> bash -c './test_probe'`（OHOS mksh 不能 exec ELF，用 CONFIG_SHELL bash 包一层）

结果（原生 OHOS 实机运行）：

```
pangomm 2.56.2: all 4 checks passed
```

断言明细（4/4）：

| # | 断言 | 结果 |
|---|------|------|
| 1 | `Pango::FontDescription fd("Sans 12"); fd.get_family() == "Sans"` | PASS |
| 2 | `fd.get_size() == 12 * Pango::SCALE` | PASS |
| 3 | `!Pango::AttrList().get_iter().next()`（默认构造的列表必为空；2.56.2 无 C++ begin()/end()，next() 是可直接断言"空"的公开 API） | PASS |
| 4 | `PANGOMM_MAJOR_VERSION >= 2`（pangommconfig.h 由包提供） | PASS |

## 通过率

上游测试 0 个（不存在）；test_package 4/4 断言 PASS。总体：**PASS**。

## 备注

- `Pango::init()` 在 main 首行调用（值对象 API 的前置要求），实际执行无异常。
- 测试为纯内存值对象操作，不依赖字体文件/渲染后端/X11/网络，鸿蒙非交互环境安全。
