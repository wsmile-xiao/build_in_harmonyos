# libforms (XForms) — HarmonyOS PC 适配

XForms 图形界面工具库：`libforms`（窗体/控件）、`libflimage`（图像与 PostScript 转换），
以及两个命令行工具 `fdesign`（界面设计器）与 `fd2ps`（表单转 PostScript）。

- 上游: https://savannah.nongnu.org/projects/xforms/ （发布名 xforms）
- 适配版本: 1.2.4（archives/l/libforms/1.2.4/）
- 构建系统: autotools（树内构建）；`--disable-gl --disable-demos --disable-docs`
- 依赖: libjpeg/10、libx11/6.4.0、libxpm/3.5.17、xorgproto/2025.1
- 状态: built（conan create + test_package 2/2、conan-verify G0-G3、W3 全过，见 1.2.4/notes.md）

要点：clang 15 需 `-fcommon`（上游 curobj 共享符号方言，E491）；生成的 forms.h 须树内构建预生成；
无 X server 平台的消费者证据按 E530 双可执行 test_package 承载，不宣称 GUI 可用。
