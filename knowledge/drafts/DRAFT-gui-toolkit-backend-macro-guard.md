# 无 X11 后端平台上的 GUI 库语言绑定：X11-only 符号编译期未声明，应按工具包自身后端宏（GDK_WINDOWING_X11）源码守卫并复用上游桩分支（无条件 -D 宏与平台名硬编码均禁止）

## 场景

lablgtk3 3.1.5（OCaml GTK3 绑定，C stub 直接 `#include <gdk/...>`）适配
HarmonyOS PC。OHOS 无 X11/Wayland 原生后端，仓内 gtk/3.24.43 以 **broadway-only**
构建（`x11_backend=false, broadway_backend=true`）。这是「后端可选 GUI 工具库 ×
源码级消费者」组合在无后端平台上的通例问题，不限 lablgtk3、不限 OCaml。

## 现象

`ci/round-01/build_and_test.log:1829`：

```text
ml_gdk.c:435:32: error: use of undeclared identifier 'AnyPropertyType'
                               AnyPropertyType, 0,
```

`ci/round-01/build_and_test.log:3140-3144`（未声明 → 隐式声明 → 类型不兼容链）：

```text
ml_gtk.c:931:7: warning: call to undeclared function 'gtk_plug_new'; ISO C99 ...
ML_1 (gtk_plug_new, GdkNativeWindow_val, Val_GtkWidget_window)
ml_gtk.c:931:7: error: incompatible integer to pointer conversion passing 'int'
  to parameter of type 'GtkWidget *' (aka 'struct _GtkWidget *')
```

## 根因

1. **平台事实（第一手实证）**：安装的 gtk 包 `gdkconfig.h:13-17`——
   `#undef GDK_WINDOWING_X11` / `#define GDK_WINDOWING_BROADWAY`（Wayland/Win32/
   Quartz 同样 undef）；X11 专用头 `gdk/gdkx.h` **不随 broadway-only 包安装**；
   `gtk/gtkplug.h` 内容本身以 `#ifdef GDK_WINDOWING_X11`（:34）/`#endif`（:101）
   守卫——即工具包自己的契约就是「X11 API 只在后端宏下存在」。
2. **上游缺口**：lablgtk3 绑定源码的平台分支只覆盖 `_WIN32/HAS_GTKQUARTZ`，
   缺「X11 后端未启用」第四分支：ml_gdk.c 无条件 include gdkx.h（该头缺失时先死
   在 include 行），函数体另引用 X11-only 符号——`AnyPropertyType`（X11 atom 宏）、
   `gtk_plug_new`/`gtk_socket_*`、`ml_gtkwindow_init` 里的 plug/socket get_type
   注册。即使头文件守卫补上，函数体符号仍会以 r1 的形态未声明。
3. **失败形态**：宏类符号（AnyPropertyType）→ `use of undeclared identifier`；
   函数类符号（gtk_plug_new）→ 隐式声明按 int 返回 → `incompatible integer to
   pointer conversion` 报错。
4. **隐藏爆炸点**：`ml_gtkwindow_init` 的 plug/socket `get_type` 注册若不守卫，
   编译可能侥幸通过、链接期 `gtk_plug_get_type` 未解析必挂——源码级守卫必须覆盖
   注册点，不能只修报错行。

## 修复

源码级两步守卫，谓词一律取**工具包自身后端宏** `GDK_WINDOWING_X11`，
全 patch 零平台宏（能力探测优于平台名硬编码）：

- **patch 0001**（ml_gdk.c）：`#include <gdk/gdkx.h>` 包进
  `#if defined(GDK_WINDOWING_X11)`——该头只随 X11 后端发布，并入上游既有
  win32/quartz 的 include 分支结构而非新造分支。
- **patch 0002**（恰五处）：把 `|| !defined(GDK_WINDOWING_X11)` 并入上游
  **既有** win32/quartz 桩分支——ml_gdk.c ×2（property_get 的 Val_unit 桩、
  `ml_GDK_WINDOW_XID` 桩）、ml_gtk.c ×3（`Unsupported(gtk_plug_new)`、
  `Unsupported(gtk_socket_steal)`、ml_gtkwindow_init 的 plug/socket get_type
  注册桩）。复用上游「非 X11 平台返回桩值」自身语义，不发明删除式改法。

## 验证

自包含探针（设备新 shell 可跑通，不依赖本 run 日志）：

```sh
GTKP=$(ls -d /storage/Users/currentUser/.conan2/p/gtkc*/p | head -1)

# ① 后端宏事实（工具包发布的平台契约）
grep -n GDK_WINDOWING $GTKP/include/gtk-3.0/gdk/gdkconfig.h
# → #undef GDK_WINDOWING_X11 / #define GDK_WINDOWING_BROADWAY（:13-17）
ls $GTKP/include/gtk-3.0/gdk/gdkx.h 2>&1
# → No such file or directory（X11 专用头不随 broadway-only 包安装）

# ② 工具包自证守卫谓词：上游自身就用该宏守卫 X11 API
grep -n GDK_WINDOWING_X11 $GTKP/include/gtk-3.0/gtk/gtkplug.h | head -2
# → 34:#ifdef GDK_WINDOWING_X11 ... 101:#endif

# ③ 三行编译探针对照（最小消费者：后端宏条件分支）
C=/storage/Users/currentUser/.conan2/p
G=$(for d in $C/glib*/p; do [ -f "$d/lib/libgobject-2.0.so" ] && echo "$d" && break; done)
HB=$(dirname "$(find $C -maxdepth 6 -path '*include/harfbuzz/hb.h' 2>/dev/null | head -1)")
INC="-I$GTKP/include/gtk-3.0 -I$G/include/glib-2.0 -I$G/lib/glib-2.0/include \
     -I$G/include/gio-2.0 -I$(ls -d $C/pango*/p | head -1)/include/pango-1.0 \
     -I$HB -I$(ls -d $C/cairo*/p | head -1)/include/cairo \
     -I$(dirname "$(dirname "$(find $C -maxdepth 7 -path '*include/gdk-pixbuf-2.0/gdk-pixbuf/gdk-pixbuf.h' | head -1)")")"
W=/storage/Users/currentUser/tmp/oh-device-porting-v2/gdkprobe.$$
mkdir -p $W && cd $W
printf '#include <gdk/gdk.h>\n#ifndef GDK_WINDOWING_X11\nint main(void){return 0;}\n#else\n#include <gdk/gdkx.h>\nint main(void){return AnyPropertyType;}\n#endif\n' > probe.c
clang $INC probe.c -o probe && ./probe; echo guarded-rc=$?
# → guarded-rc=0（按工具包后端宏守卫：broadway-only 平台编译运行通过）
clang -DGDK_WINDOWING_X11 $INC probe.c -o probe2 2>&1 | grep -m1 'fatal error'
# → fatal error: 'gdk/gdkx.h' file not found（无条件 -D 强开宏：换一种死法，禁）
```

端到端：round-03/04 权威 CI（五处守卫落地后）PASS；T2 无显示器探针真机运行
通过；T3 消费者编译链接通过（build-only，运行级按 E471 分类排除）。

## 边界

- 适用：一切在无某 GUI 后端平台上源码级消费多后端工具库头文件的绑定/消费者；
  守卫谓词必须取自工具包发布的后端宏集合（GTK 系为 gdkconfig.h 的
  GDK_WINDOWING_*；其他工具库找同类发布面）。
- 反例：真正需要 X11 运行时能力的消费者（X 客户端工具、抓屏）不可用宏守卫"绕过"，
  应按 E463/E471 分类为运行级不可用，勿混入编译期修复。
- 与 imlib2 草稿的分工：库自带 `X_DISPLAY_MISSING` 宏、需**配方注入**消费者编译
  环境的 → DRAFT-imlib2-1.9.1-x-display-missing-consumer-macro（宏注入法）；
  绑定**源码自身缺平台分支**、需源码级补后端宏守卫并复用上游桩的 → 本条
  （源码守卫法）。错误签名可区分：`'X11/Xlib.h' file not found` vs
  `use of undeclared identifier`。
- 前置检查：先 grep gdkconfig.h 确认后端集合、ls 确认专用头是否随包安装，
  再定守卫清单；注册点（get_type）与报错行都要过一遍，防链接期隐藏爆炸点。

## 查重

检索面：本 run worktree `knowledge/`（graph 544 文件 + drafts；index.tsv 766 行）。

| 检索词 | 命中 | 判定 |
|---|---|---|
| `GDK_WINDOWING_X11` | 0 | 官方面零命中 |
| `gdkx\.h\|AnyPropertyType\|gtkplug` | 0 | 官方面零命中 |
| `X11` | 13 文件 | 逐一核对相关者：E463（broadway 构建+无显示消费者验证，机理为平台无 X11/Wayland+签名工具，无编译期守卫内容）、E471（显示测试分类）、E527（broadway-native-tools-wrapper，错误签名 `Dependency .* not found` 族）、E480/E309/E522/E530/E350/E398（.pc/X11 路径/其他主题）——均不覆盖「绑定源码缺后端分支 → 后端宏源码守卫+上游桩」机理与修法 |

**最近邻（查重面内，必须挂钩）**：`drafts/DRAFT-imlib2-1.9.1-x-display-missing-consumer-macro`——
同问题类（无 X11 构建导致消费者编译失败），机理与修法逐项不同：

| 维度 | imlib2 草稿 | 本条 |
|---|---|---|
| 缺口所在 | 库自带 `X_DISPLAY_MISSING` 宏困在构建期 config.h，未达消费者 | 绑定源码自身缺「后端未启用」平台分支 |
| 修法 | 配方向消费者 cpp_info.cflags 注入 `-DX_DISPLAY_MISSING`（宏注入） | 源码级 `GDK_WINDOWING_X11` 守卫 + 复用上游桩分支（源码守卫） |
| 错误签名 | `fatal error: 'X11/Xlib.h' file not found` | `use of undeclared identifier` / `incompatible integer to pointer conversion` |
| 守卫谓词出处 | 库的 configure 产物 | 工具包发布的 gdkconfig.h 后端宏集合 |

E463（broadway-only 构建与无显示验证）与 E527（broadway 后端 wrapper 三件套）
为同平台事实族的相关条目：E463/E527 解决「构建/验证」面，本条解决它们未覆盖的
「绑定源码编译面」；若知识库主编倾向与 imlib2 草稿合并为「无 X11 平台消费者
编译失败族」，本条可作该族第二实例（机理/修法/签名三重差异仍成立）。

同 stem 草稿：DRAFT-gui-toolkit-backend-macro-guard.kv
