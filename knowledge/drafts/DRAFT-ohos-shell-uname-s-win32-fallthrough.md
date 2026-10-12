# DRAFT-ohos-shell-uname-s-win32-fallthrough — shell 构建系统 `uname -s` 平台探测：HarmonyOS 落 Win32 默认分支

## 错误特征

自带平台探测的自研 shell 构建系统（quickbuild/qb、手写 configure、bootstrap）在
OHOS 真机上 configure 时，平台被判成 **Win32**，随后在与目标平台毫无关系的位置
报错。RetroArch 1.22.2 实例：

```
$ ./configure --disable-... --build/--host 未用
Checking operating system ... Win32
Checking for suitable working C compiler ... clang works
Checking for suitable working C++ compiler ... clang++ works
Checking for windres ... none
Error: Cannot proceed without windres.
```

C 编译器明明可用，却因为「被判成 Windows」去要 `windres`。更隐蔽的情形是不报错、
而是静默选错整套 Win32 代码路径（Makefile 走 `.obj`、源码走 `#ifdef _WIN32`），
到编译期才连环失败。

## 触发条件

- 平台：OHOS 真机（`uname -s` = **HarmonyOS**，内核 sysname）。
- 阶段：**configuration**（shell 探测期）。
- 代码模式：`case "$(uname -s)" in ... *) OS="Win32";;` —— 默认分支给了一个
  「能跑下去」的假平台而不是报「unknown platform」。
- 高发形态：为游戏机/嵌入式写的手写构建系统（RetroArch qb、各类 retro 项目）。

## 根因分析

`uname -s` 返回内核 sysname。HarmonyOS 的 sysname 是 `HarmonyOS`，不在多数探测
脚本的枚举里：

```sh
# RetroArch qb/qb.system.sh（修复前）
case "$PLATFORM_NAME" in
    'Linux') OS='Linux';;
    *'BSD')  OS='BSD';;
    'Darwin') OS='Darwin';;
    ...
    *) OS="Win32";;        # ← HarmonyOS 落到这里
esac
```

默认分支是 `Win32`（历史原因：老脚本默认「跑在 Windows 上」）。于是 Windows 专属
检查（windres/d3d/dinput/dsound）全部启动。HarmonyOS PC 实际是 **Linux/musl
(bionic) 用户态**，正确归类是 Linux 族。

### 诊断要点

- 看到configure 打印 `Checking operating system ... Win32` 就该停——OHOS 上
  一切后续 Win32 检查都是噪声。
- `grep -n "uname -s" configure qb/*.sh` 直接定位探测点。

## 修复方案

**把 `'HarmonyOS'` 并入 Linux 分支**（一行补丁）：

```diff
-       'Linux') OS='Linux';;
+       'Linux'|'HarmonyOS') OS='Linux';;
```

- 前缀/glob 匹配的脚本同理加 `HarmonyOS*`。
- 之后按 Linux/musl 语义正常走特性探测（pthread/dl/socket 等）。
- 实证：RetroArch 1.22.2 补丁 0001（qb/qb.system.sh），configure→make -j 全量
  通过，`retroarch --version` rc=0，上游 libretro-common 5 套件 127/127。

回退：脚本支持 `OS` 环境变量覆盖时（qb 允许）可 `export OS=Linux` 绕过；不如
补丁稳（子脚本可能重跑探测）。

## 禁止做法

| 禁止 | 原因 |
|------|------|
| 去装 windres / mingw 工具链 | `Cannot proceed without windres` 是「被当成 Win32」的**结果**，不是缺工具；装了继续连环失败 |
| 篡改 `uname` 输出 / 改 sysname | 系统标识不可篡改；探测方归类错误才是根因 |
| 在 C 源码里加 `#ifdef __OHOS__` 绕 | 平台归类属构建系统层；源码平台宏违反 R8（实测被 AI 检视 P1 打回） |

## 边界（与既有条目的区别）

- **E532** 是 **CMake 族**平台探测（`CMAKE_SYSTEM_NAME` / `elseif UNIX` /
  `WIN32` / `FATAL_ERROR`），trigger_tool=cmake；本条是 **shell 族**
  （configure/case `uname -s`/默认分支），trigger_tool=configure、错误签名
  （windres / `OS="Win32"`）不同，修复位置也不同（改 shell case vs 改
  CMakeLists）。
- E007/E564 是 autotools **config.guess/config.sub** 族；本条不经过 config.guess。

## 验证

```sh
uname -s                                  # HarmonyOS
./configure ... 2>&1 | grep 'operating'   # 修复后: Checking operating system ... Linux
grep -n "HarmonyOS" qb/qb.system.sh       # 补丁命中
```
