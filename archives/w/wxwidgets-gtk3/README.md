# wxwidgets-gtk3

wxWidgets 3.2 的 GTK3 GUI 变体，为 HarmonyOS PC 提供 wx GUI 能力
（wxCore/wxAdv/wxHtml/wxAUI/wxSTC 等完整 GUI 库集），是 codeblocks 等
wx 系 GUI 应用的前置依赖。

与 `wxwidgets`（base 变体）的区别：base 只构建无 GUI 的 wxBase 库；
本包以 `wxUSE_GUI=ON + wxBUILD_TOOLKIT=gtk3` 对接制品仓 `gtk/3.24.43`
（broadway 后端）。wx 3.2.10 GTK 端口中所有 X11 专有代码均有
`GDK_WINDOWING_X11` 编译守卫，在 broadway 后端下编译为空，因此无需
X11/Wayland 客户端库即可完整构建 GUI 库集。

- 上游: https://github.com/wxWidgets/wxWidgets
- 许可: wxWindows Library Licence
- 版本: 3.2.10（与 base 变体同源同版本号，不同包名区分变体）
