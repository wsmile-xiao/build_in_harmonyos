# implot 0.8 测试报告

## 上游测试

- 上游 v0.8 tarball 无测试目录、无构建系统、无测试注册入口（仅库源码
  implot.cpp / implot_items.cpp 与演示文件 implot_demo.cpp）。
- 上游静态用例总数：0；实际执行：0；跳过：0（N/A 口径，非 0/0 通过）。

## 适配后测试（conan create 内真实执行）

test_package（消费者测试，链接 implot::implot + imgui::imgui 全静态依赖链，
设备上以 headless 方式运行）：

| # | 检查项 | 结果 |
|---|--------|------|
| 1 | implot 上下文创建 | PASS |
| 2 | 样式 Push/Pop 往返（LineWeight 3.0） | PASS |
| 3 | 1.92 key-chord 输入映射默认值（QueryToggleMod == ImGuiMod_Ctrl） | PASS |
| 4 | headless 字体图集预构建（Fonts->Build） | PASS |
| 5 | BeginPlot/PlotLine/EndPlot 窗口内生命周期 | PASS |
| 6 | 渲染几何输出 vtx=516 idx=852（>0） | PASS |

合计：6/6 通过，0 失败，0 跳过。
命令输出：`ALL 6 CHECKS PASSED`（reports/conan-create.log）。

## 验证门禁

- conan-verify：G0/G1/G2(conan create)/G3/G4/L2/L4/L5 全部 PASS。
- finish W3 本地 CI 模拟：L0 pass（含 JC/JUNK/R36/R37/R38）、L1 test_package 执行通过。
- 依赖：imgui/1.92.2b（ohpcd 制品仓 plain ref，conan install --build=never 实测可下载）。
