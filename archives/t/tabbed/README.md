# tabbed

`tabbed` 是 suckless 项目的极简 X11 **标签容器**：它自己建一个带标签栏的窗口，
把命令行给出的任意程序作为子窗口嵌进来（通过 XEmbed 协议），程序本身不需要知道
自己被打上了标签。发布包一次产出两个程序：

- `tabbed` — 容器窗口本体，负责标签栏绘制、窗口嵌入与事件循环。
- `xembed` — 极小的包装程序，被 `tabbed` 用来启动子程序并设置 `XEMBED` 环境变量；
  它的源码不直接调用 Xlib，但上游 Makefile 的单条链接规则把与 `tabbed` 相同的
  `-lX11 -lfontconfig -lXft` 也链进了它（W3 日志的 `clang -o xembed xembed.o ...`
  一行可直接复核），所以**运行期同样需要这套 X 闭包**，不是零依赖程序。

## OpenHarmony 适配

- 源码：官方发布源 dl.suckless.org 的 tabbed-0.9.tar.gz（R39 单值 URL，无镜像 fallback）
- 构建系统：裸 `.POSIX:` Makefile（无 configure、无 CMake、也没有 dmenu 那套 config.mk）
- 依赖（制品仓 ohpcd 均已发布）：libxft/2.3.9、libx11/1.8.13、fontconfig/2.18.3、
  xorgproto/2025.1 —— 上游链接行写死 `-lX11 -lfontconfig -lXft`，
  且源码 include 了 `X11/Xft/Xft.h`，Xft 与 fontconfig 是硬依赖不是可选项
- 配方侧的三个必要动作：
  1. 显式注入交叉 clang（`.POSIX:` 会让 GNU make 的隐式 CC 变成不存在的 `c99`）；
  2. 依赖的 `-I` 走 CFLAGS、`-L` 走 LDFLAGS —— 上游的 `TABBED_CPPFLAGS`
     从不引用 `${CPPFLAGS}`，走 CPPFLAGS 会被无声丢弃；
  3. 不使用 `make install`（`PREFIX` 是普通 `=` 赋值），产物在 `package()` 内手工放置，
     两个 ELF 都做 OHOS 自签。
- 上游零测试；`test_package/test_tabbed.sh` 用 4 条断言真实运行两个已安装程序，
  断言全部落在 stderr 文本上：上游把 `tabbed` 的所有早退路径（含 `-v`）都送进
  `die()` → `exit(EXIT_FAILURE)`，退出码不携带信息。
- 未覆盖：X server 往返（建容器窗、标签栏绘制、XEmbed 事件循环）在无显示服务端的
  本环境明确记为未验证。
- **R40 标注（需人工确认适配完整性）**：本包属图形/窗口类，配方层没有任何平台补丁
  （`patches: []`）、也没有 `__OHOS__` 分支——它依赖的 Xlib/Xft/fontconfig 闭包本身
  已由上游 X 端口提供，tabbed 只是消费者。因此"编译通过 + 4 条无头行为断言"不等于
  真实窗口管理行为已验证，合并后需在带 X server 的环境人工确认一次。
