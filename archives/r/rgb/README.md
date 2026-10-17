# rgb（X.org RGB 颜色名称数据库）

## 简介

`rgb` 是 X Window System 的颜色名称数据库组件。本包发布上游默认（text）形态：

- `showrgb`：按颜色名查 RGB 值（或整库倒出）的命令行工具，纯文本库读取，**不需要 X server**
- `share/X11/rgb.txt`：782 条颜色名 → RGB 值映射，X11 应用颜色名解析的基础数据
- `share/man/man1/showrgb.1`

## 软件信息

- **上游源码**: https://gitlab.freedesktop.org/xorg/app/rgb
- **官方发布 tarball**: https://www.x.org/releases/individual/app/rgb-1.1.1.tar.gz
- **分类**: X11 工具
- **许可证**: MIT/X11

## 鸿蒙适配要点

| 要点 | 说明 |
|------|------|
| 构建系统 | autotools；X.Org 发布 tarball 自带 configure，**无需 autoreconf / util-macros** |
| 依赖 | 仅 `xorgproto/2025.1`（提供 `xproto.pc` 与 `<X11/Xos.h>`、`<X11/Xfuncs.h>`） |
| config.guess | 2024-07-27 版不认 `uname -s`=HarmonyOS，需加 `*:HarmonyOS:*:*)` 分支（config.sub 已内置 linux-ohos*，不用改） |
| HMDFS | E011/E118：configure 内嵌 config.status 的 `umask 077` mktemp 目录不可写 → 改 022；并用 `ac_pwd` 回退兜底 getcwd 缺失 |
| 运行期 | 不连 X server，`DISPLAY` 未设置即可运行 |
| **平台边界** | **`rgb` 转换器二进制（rgb.txt → .dir/.pag）在本平台无法构建**：它被 automake 的 `RGB_DB` 条件包住，仅 `--with-rgb-db-type=dbm\|ndbm` 时编译，而那两个分支额外要求 `PKG_CHECK_MODULES(XORG,[xorg-server])`（xorg-server 未发布）与 dbm/ndbm 提供方（OHOS NDK sysroot 无 `dbm.h`/`ndbm.h`）。详见 `1.1.1/notes.md` §1–§2 |

## 可用版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.1.1 | ✅ built（conan-verify 通过，待 CI release） | 2026-09-23 |

## 预编译依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| xorgproto | 2025.1 | X11 协议头文件 + `xproto.pc`（ohpcd 已发布 OHOS armv8 二进制） |

## 补丁清单

两个补丁都在 `1.1.1/conandata.yml` 的 `patches:` 中声明，由 `build()` 首行
`apply_conandata_patches(self)` 在解包后真实应用（`patch_type: portability`）：

| 补丁 | 说明 | 类型 |
|------|------|------|
| 0001-config.guess.patch | 识别 HarmonyOS → `aarch64-unknown-linux-ohos`（因此配方无需 `--build/--host`） | 平台 |
| 0002-configure.patch | E011/E118 `umask 077`→`022`；`ac_pwd` getcwd 回退 | 平台 |

## 已知限制

- `showrgb` 的默认颜色库路径 `RGB_DB` 是 **configure 期烤入的绝对路径**（指向本包安装目录下的
  `share/X11/rgb`，text 模式自动补 `.txt`）。因此**包换 `CONAN_HOME` 或搬家后无参运行会失败**，
  需显式给 dbname；消费方在自己的 prefix 下另装一份 `rgb.txt` 时也应显式传路径。
- 只发布 text 形态：`rgb` 转换器（`.dir`/`.pag`）本平台给不了，见上「平台边界」。

## 用法

```bash
showrgb                      # 倒出整库，用包内烤入的默认库（包未搬家时）
showrgb <pkg>/share/X11/rgb   # 显式给 dbname（man 页口径：不带 .txt 后缀），<pkg> 为包安装根目录
```
