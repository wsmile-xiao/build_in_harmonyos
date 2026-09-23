# E429 — 无原生显示后端的桌面 GUI 应用在 OHOS PC 的运行时适配模式（curtain 0.3 实例）

> 草稿（draft）：与归档适配同一原子 PR（#10116，分支 `feat/curtain-0.3`）交付，待主编评审与编号。
> 贡献者：kasumizawa-miyuu <241250031@smail.nju.edu.cn>

## 错误特征

```
Gtk-WARNING **: cannot open display:
（进程退出码 1）
```

或（强制 Broadway 时）：

```
display type = GdkBroadwayDisplay  composited=1
```

以及反向确认后端面的字串证据：

```
libgtk-3.so: broadway 命中，x11/wayland 未命中（构建时 --enable-x11-backend=no 等）
```

## 触发条件

- 构建系统：上游 autotools（GTK3），适配层 CMake（本条目描述的是运行时适配模式，非构建问题）
- 阶段：runtime（窗口/交互行为）
- 场景：上游 UI 工具包在 OHOS 只发布了 Broadway（浏览器输出）后端，没有 X11/Wayland 等原生显示后端；
  应用需要在 HarmonyOS 原生桌面上产生窗口级行为（全屏覆盖、遮罩、点击穿透、置顶等）
- 实例：curtain 0.3（GTK3 桌面遮罩小工具，行为=全屏幕布 + 四边拖拽揭开 + 揭开区点击穿透 + 右上角关闭）

## 根因分析

1. OHOS 发布的 GTK 3.24.43 构建时仅启用 Broadway 后端（HTML5/浏览器），X11/Wayland 关闭；
   原生进程没有 `DISPLAY`/`WAYLAND_DISPLAY`，`gtk_init` 直接失败（`cannot open display`）。
2. 即便自启 `broadwayd`，GTK 的输出也只是**浏览器内的画布**：不能覆盖 HarmonyOS 原生桌面，
   也不提供桌面窗口的 input shape/置顶/全屏语义。把 Broadway 当作完成证据属于功能替换。
3. 上游程序的行为并不都依赖 GTK：curtain 的核心是**窗口几何状态机**（`src/callbacks.c` 的按压/释放
   四边揭开、回盖、最小尺寸钳制、关闭热区）与**缩放语义**（`src/utils.c::scale_surface`），
   这两部分与平台无关，可以移植；真正缺的是**宿主窗口层**。
4. 因此适配不是“打补丁让 GTK 跑起来”，而是**换宿主 + 移植行为核心**：用 ArkUI 原生宿主提供窗口与输入，
   把行为核心放进可独立测试的 C 代码。

## 解决方案

### 推荐方案（curtain 0.3 已验证）

1. **不改上游源码**：所有补丁都是新增文件（本实例 34 个），上游三源文件保持原样。
2. **ArkUI 原生宿主**（DevEco 工程，独立包名）：主窗口全屏沉浸 + 装饰隐藏，作为“幕布窗口”；
   触摸事件驱动 C 核心。
3. **行为核心移植为无依赖 C**：
   - 几何状态机逐分支移植 `callbacks.c`（四边揭开/回盖/最小 25px/关闭热区）；
   - 缩放移植 `utils.c::scale_surface` 语义：平台 `image` 模块解码 PNG 得到 RGBA，
     C 侧做双线性采样 + 边缘镜像缩放到屏幕尺寸（避免引入 cairo 及其 20+ 依赖链）。
4. **窗口矩形=幕布/组件矩形**（关键非直觉点）：
   - 初始：全屏覆盖桌面；
   - 拖拽释放后：`recover()`（若最大化）+ `moveWindowToAsync` + `resizeAsync` 把窗口调到剩余区域；
   - 窗口之外即桌面 → 揭开区域天然可见、天然可点击（等价上游 `gtk_widget_input_shape_combine_region`）。
5. **资源注入**：二进制资源（上游 `curtain.png`）由配方在 `package()` 从上游源码树复制进宿主
   `rawfile`，不进补丁管线；文本资源（SVG 图标）可用普通文本补丁。
6. **验证组合拳**：
   - 无头 C 回归测试（本实例 `bin/curtain_check` 28/28，覆盖几何与缩放）；
   - `test_package` 消费者断言（16/16，含 `libace_napi.z.so` NEEDED 等）；
   - 真机逐行为验证：`uinput` 注入拖拽/点击 + `snapshot_display` 截图 + hilog 摘录
     （本实例全屏遮罩/横纵揭开/点击穿透/回盖/关闭/重启全部通过）。
7. **如实记录限制**：`setWindowTopmost` 需系统权限（实测返回 201）；被点击拉起的窗口可盖住幕布；
   系统 Dock 始终绘制在幕布之上；自由窗口顶部热区可能占用 X 热区（最大化/全屏下正常）。

### 关键实测数据（curtain 0.3）

| 行为 | 结果 | 证据 |
| --- | --- | --- |
| 全屏遮罩 | PASS | 启动后整屏被幕布覆盖（device-verify/01-launch.jpeg） |
| 拖拽揭开（右缘） | PASS | 窗口变为 (0,0,1700,2080)（02-peel-right.jpeg + 日志） |
| 纵向揭开 | PASS | 窗口变为 (0,500,1700,2080)（02b-peel-top.jpeg + 日志） |
| 点击穿透 | PASS | 点击露出区无应用触摸日志，桌面/浏览器收到点击（03-click-through.jpeg） |
| 拖拽回盖 | PASS | applyRect (100,0,3020,2080)（04-recover.jpeg） |
| 右上角 X 关闭 | PASS | quit requested，进程退出（05-close.jpeg） |
| 重启 | PASS | 重启后全屏遮罩与交互正常 |

### 禁止做法

- 不要以 Broadway/浏览器渲染、单纯编译通过、无关截图冒充桌面遮罩/窗口行为完成。
- 不要用空实现/桩替换上游核心行为来制造“编译通过”。
- 不要把一个 GUI 应用的**构建级**适配经验（工具包装、测试分类）误当作**应用级**行为适配完成。

## 验证

```bash
# 1) 后端面与直启签名（构建级反证）
strings <gtk-pkg>/lib/libgtk-3.so | grep -E "broadway|wayland|x11"   # 仅命中 broadway
./curtain 2>&1 | grep "cannot open display"                          # 上游直启失败的稳定签名

# 2) 适配后无头回归 + 消费者测试
conan create archives/c/curtain/0.3 -pr:h=<profile> -pr:b=<profile> --build=missing
# 期望：curtain_check 28/28；test_package 16/16；G0-G4 PASS

# 3) 真机逐行为验证（安装签名 HAP 后）
hdc install -r entry-default-signed.hap
hdc shell aa start -b com.kasumizawamiyuu.curtainhost -a EntryAbility
hdc shell uinput -M -g 3000 1000 1700 1000 800     # 右缘揭开
hdc shell snapshot_display -f /data/local/tmp/curtain.jpeg
```

## 关联条目

- 相关：E463 / E471 / E527（同为 OHOS GTK Broadway-only 背景，但均为**构建级**：HMDFS 资源编译、
  无显示服务下的测试分类、原生工具包装）；E321（GL 兼容层，属“补 API 面”）；E474（ArkUI 原生
  消费者验证契约，属“怎么验收”）。
- 差异（新增价值）：本条是**应用级运行时适配模式**——当显示后端缺失导致上游窗口层不可用时，
  如何以“ArkUI 原生宿主 + 行为核心 C 移植 + 窗口矩形=组件矩形”重建行为，并给出可复制的验证组合拳；
  现有条目无一条覆盖“宿主替换 + 窗口几何等价实现遮盖/穿透”。
