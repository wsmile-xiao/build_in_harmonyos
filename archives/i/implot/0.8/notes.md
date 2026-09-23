# implot 0.8 适配记录

## W0/W0b

- 任务语言 C++，源码主体 C++，语言预检匹配（R47 通过）。
- 上游 tag v0.8 tarball（GitHub epezent/implot），SHA-256
  `157e9302bb0e07e64a0762a8c39acc97605b57d3160b948593b7227132556d35`，官方 HTTPS URL。
- 2026-09-02 会话曾因 `imgui` 未在制品仓发布而 dependency_missing 止损；2026-09-05 实测
  ohpcd 制品仓已有 plain ref `imgui/1.92.2b`（`conan install --build=never` 下载二进制成功），
  W0 阻塞解除。上游 archives/i/imgui/1.92.2b 亦已合入（status: built）。
- 该库无 Autotools/CMake/Meson 构建入口（README 要求与 Dear ImGui 源码共同集成），
  按仓库 imgui 先例采用配方自生成 CMakeLists 的固化方案。

## ImPlot 0.8 × Dear ImGui 1.92.2b 兼容性

ImPlot 0.8（2020）针对 ImGui ~1.74 API 编写，与 1.92.2b 的差异以补丁
`patches/0001-imgui-192-api-migration.patch` 修复（3 个文件，7 类符号迁移）：

1. `ImGuiKeyModFlags`/`ImGuiKeyModFlags_*` → `ImGuiKeyChord`/`ImGuiMod_*`；
2. `#define IMGUI_DEFINE_MATH_OPERATORS` 提前于 `imgui.h`（1.92 移除内建 ImVec2/4 运算符）；
3. `ImPool::GetSize()` → `ImPool::GetBufSize()`；
4. `ImDrawCornerFlags_All` → `ImDrawFlags_RoundCornersAll`；
5. `ImGui::ItemHoverable(bb,id)` → 三参 `(+ImGuiItemFlags_None)`；
6. `ActiveIdUsingNavInputMask`/`ActiveIdUsingKeyInputMask` → `ActiveIdUsingAllKeyboardKeys`；
7. 竖排文本字形访问 `font->FontSize`/`font->FindGlyph` → `ImFontBaked` 路径
   （`font->GetFontBaked(g.FontSize)`，缩放系数置 1.0f：baked 尺寸即当前字号）。

探索性验证（本任务私有目录，非 worktree）：clang++ -fsyntax-only 两个编译单元零错误；
静态库 + headless consumer 链接运行成功，真实绘图产出 vtx=516 idx=852。

## 上游测试

- v0.8 tarball 无测试目录、无构建系统、无测试注册入口（仅库源码 + implot_demo.cpp 演示）。
- 上游静态用例总数 0，实际执行 0，跳过 0（N/A 口径，非 0/0 通过）。
- 按 R34 设计真实消费者测试（test_package，6 项断言全过）：
  上下文创建、样式 Push/Pop 往返、1.92 key-chord 输入映射、headless 字体图集构建、
  BeginPlot/PlotLine/EndPlot 生命周期、渲染顶点/索引 > 0（vtx=516 idx=852）。

## 路径 B 知识贡献

两条经查重（E216/E217/E221/E464/E471 等）与 draft-review 的新知识草稿：

- `DRAFT-implot-imgui-headless-atlas`（verdict: create）：imgui 1.92 headless 消费者
  必须先 `Fonts->Build()` + `GetTexDataAsAlpha8()` 再 NewFrame，否则空图集解引用
  SIGSEGV；消费者以 `LINKER:--as-needed` 丢弃未引用的 ace_ndk.z/EGL/GLESv3，
  避免拉入应用级 Ace/NAPI 运行时链造成 libc++ 符号冲突。
- `DRAFT-conan-cmaketools-transitive-includedirs`（verdict: review-similar→E217，
  实质不同：E217 是 install 子目录漏装，本条是 CMakeDeps 对传递依赖 includedirs
  序列化为空的不对称行为）：包装包 package_info 显式 `includedirs.extend(依赖)`。
- 2026-09-02 的 `DRAFT-implot-unpublished-imgui-dependency` 前提已被 imgui 发布推翻，
  且其通用规则已被 SKILL R36 覆盖，已删除（未提交过）。

## 已知限制

- `implot_demo.cpp`（约 11k 行演示）未纳入构建与测试；它不是测试套件。
- 上游无自动化测试，"通过率"以上游 0/N/A 口径如实填报；消费者测试 6/6 通过。
---

**编译结束**: 2026-09-05 15:13
**最终状态**: built
