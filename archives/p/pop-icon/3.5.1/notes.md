# pop-icon 3.5.1 适配笔记

## 概述

把 System76 的 Pop 图标主题适配为 HarmonyOS PC 的 Conan 纯资源包。Pop 是
Pop!_OS / GNOME 的默认图标集，交付物是可被 XDG 图标查找机制直接使用的
`index.theme` + 图标树。

## 上游形态

```
icon-theme-3.5.1/
├── Pop/          6534 个文件：6236 SVG + 140 .cur + 8 .ani + 148 无扩展名光标
│                 + index.theme + cursor.theme；顶层 11 个尺寸目录
├── Pop-Dark/     2262 个文件：2261 SVG + index.theme；顶层 2 个尺寸目录
├── src/          1226 个 SVG 源稿（渲染流水线的输入）
├── master-render.py / meson.build / debian/ / svgo.config.js
├── index.theme.in / cursor.theme.in（模板）
└── COPYING / LICENSE / AUTHORS
```

上游 `meson.build` 只有一句 `install_subdir('Pop', install_dir: <prefix>/share/icons)`
加一个 `gtk-update-icon-cache` 的 post_install 脚本 —— **没有任何编译步骤**。

## 安装内容

```
share/icons/Pop/**            主图标集（含 index.theme / cursor.theme / cursors/）
share/icons/Pop-Dark/**       暗色图标集
licenses/{COPYING,LICENSE,AUTHORS}
```

`src/`、`master-render.py`、`meson.build`、`debian/` 是**渲染流水线**而非主题本体，
不安装（与已合入的 papirus-icon 同形态）。消费方通过 `POP_ICON_THEME_DIR`
与环境变量 `XDG_DATA_DIRS`（buildenv/runenv 均前置 `share/`）定位主题。

## 为什么没有编译步骤

上游 meson 的安装阶段不涉及编译器；`master-render.py` 是把 `src/` 的 SVG 渲染成
主题内图标的**离线**工具（依赖 Inkscape/rsvg），上游仓库里已经带了渲染好的结果，
本包直接交付该结果。因此配方 `package_type = "unknown"`、不声明 `settings`、
`build()` 只做本体自检，并且不创建 `commands.json`、不伪造二进制测试（E255 的 forbid_1）。

## 上游测试情况

上游没有测试目录、测试框架或 CI 测试阶段（`meson.build` 里没有 `test()`）。
**上游用例数 N = 0。**

## 新增自检（test_package/test_pop_icon.py）

验证的是主题本体，而不是"文件存在"：

| 断言组 | 内容 |
|--------|------|
| 结构 | `share/icons` 下**只有**两套主题；`Pop/`、`Pop-Dark/` 顶层尺寸目录集合与上游逐一相同 |
| index.theme | 每套主题的 `index.theme` 含 `[Icon Theme]` 与 `Name=`；`Pop/cursor.theme` 同样是合法主题声明 |
| 体量 | 各尺寸目录的文件数逐个对比（如 `16x16`=829、`cursors`=296、`Pop-Dark/22x22`=1131）；主题文件总数 6534 / 2262；SVG 数 6236 / 2261 |
| SVG 本体 | **8497 个 SVG 逐个** 校验：合法 XML + 根元素为 `svg`；每个尺寸目录都必须含 SVG |
| 光标 | `cursors/` 的 140 个 `.cur` 逐个校验 CUR 容器（`00 00 02 00`）、8 个 `.ani` 逐个校验 `RIFF…ACON`、148 个无扩展名 X11 光标存在 |
| index.theme 覆盖率 | `Directories=` 列 154 项；**所有真正含图标的叶子目录都必须被收录**，只允许上游已知的两个例外（`512x512/places`、`cursors`） |
| 纯净性 | 渲染流水线（`src/`、`master-render.py`、`meson.build`、`debian/`…）不得混进安装目录；许可证三份齐全 |

其中"index.theme 覆盖率"是最有价值的一条：图标文件都在、但 `index.theme` 没列出
对应目录时，图标在系统里是**不可见**的 —— "文件存在"类断言完全发现不了这种损坏。

## 构建与验证

纯资源包，本机即可跑完整门禁（不需要设备）：

```bash
source /home/silhouette/conanenv/bin/activate
export CONAN_HOME=/home/silhouette/.conan2-ohos
python3 scripts/ohc-run.py conan-verify pop-icon 3.5.1
```

> 注意：本机直连 GitHub 会超时，必须走 `ohc-run.py`（它的 E017 步骤会把
> GitHub URL 临时替换成 `ghfast.top` 镜像）。

## 来源

- Source URL: `https://github.com/pop-os/icon-theme/archive/refs/tags/v3.5.1.tar.gz`
- SHA256: `92e73f252e5e9c8a1124623a7d421410ef43c798a4a992955e6eb4f666f5c8a0`
- License: CC-BY-SA-4.0

---

**编译结束**: 2026-09-19
**最终状态**: built
