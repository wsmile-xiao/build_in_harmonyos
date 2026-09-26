# wm-icons 0.4.0 适配笔记

## 概述

把 `wm-icons`（Window Manager Icons）适配为 HarmonyOS PC 的 Conan 纯资源包。
它的设计核心不是"某一套图标"，而是**一份标准化的图标名清单**：`icons/names.lst`
定义 84 个语义名（`amusement`、`calculator`、`cd-player`、`window-close`…），
31 个图标集（不同尺寸/风格）各自用 PNG 或 XPM 实现这份清单的一（部分）子集，
再由窗口管理器的 rc 把语义名指向具体图标文件。

## 上游形态

```
wm-icons-0.4.0/
├── icons/                31 个图标集：828 个 PNG + 1210 个 XPM + 每集一份 _symlinks.lst
│   ├── names.lst         84 个标准图标名
│   ├── 01x01-template/ … 64x64-gant/
├── bin/                  wm-icons-config(.in)、wm-icons-fix-old-rc（#!/bin/sh 脚本）
├── doc/                  FAQ、README.*、icons.lst、wm-icons.lsm
├── etc/                  fvwm1/fvwm2/fvwm95/scwm 的 rc 模板（.in）
├── devel/ rpm/           开发与打包辅助
├── Makefile.am configure.ac config.guess config.sub …   autotools
└── COPYING / README / INSTALL / ChangeLog
```

## 安装内容

```
share/wm-icons/<31 个图标集目录>/     828 PNG + 1210 XPM + 31 份 _symlinks.lst
share/wm-icons/names.lst              84 个标准图标名
share/doc/wm-icons/                   FAQ / README.* / icons.lst
licenses/COPYING
```

## 为什么没有编译步骤

上游的 autotools 只承担**安装**职责：`icons/Makefile.am` 的 `install-data-local`
把每个选中的图标集 `tar` 进 `$(icondir)`（`tar cpf - "$iconset" | (cd $(icondir) && tar xfBp -)`），
顶层 `install-data-local` 再跑 `wm-icons-config --defaults` 生成 `_symlinks.lst` 里
定义的软链。**没有任何源文件被编译**（工程里只有 `.xpm/.png` 与 shell/perl 脚本）。

因此本配方按同样语义直接拷贝图标树，不调用 `configure`/`make` —— 也就不需要
OHOS 工具链，纯数据包可以在本机跑完整门禁。

## 有意不安装的部分（技术取舍，非遗漏）

- **`bin/`**：`wm-icons-config` 是 `#!/bin/sh` 脚本，`install-data-local` 靠它生成
  语义名软链。OpenHarmony 没有 `/bin`（E165），`#!/bin/sh` 脚本在鸿蒙上无法启动；
  且它的作用是为 fvwm/scwm 之类的窗口管理器准备软链，而这些 WM 在鸿蒙侧并不存在。
- **`etc/`**：同样是面向 fvwm1/fvwm2/fvwm95/scwm 的 rc 模板（`.in` 形态），
  目标窗口管理器不在本平台。
- `devel/`、`rpm/`：开发与打包辅助。

## 上游测试情况

上游没有测试框架、没有 `check`/`test` 目标、也没有 CI 测试阶段，**上游用例数 N = 0**。

## 新增自检（test_package/test_wm_icons.py，18 条断言）

| 断言组 | 条数 | 内容 |
|--------|------|------|
| 图标集结构与体量 | 3 | 31 个集合目录集合与上游一致；每个集合的文件数**逐字一致**（31 项 `{目录: 文件数}` 映射）；文件总数 2069 |
| 每集符号链接表 | 1 | 每个集合都带自己的 `_symlinks.lst` |
| 标准名清单 | 3 | `names.lst` 存在；列出 84 个名字；无重复；不带扩展名 |
| 覆盖率（最关键） | 2 | **所有集合的并集覆盖全部 84 个标准名**；`16x16-kde` 这一个集合完整实现全部 84 个 |
| 图像本体 | 3 | 828 个 PNG 逐个校验 PNG 魔数；1210 个 XPM 逐个校验 `/* XPM */` 头；不存在第三种文件 |
| 文档与许可 | 2 | `share/doc/wm-icons` 含 FAQ / README.* / icons.lst；`licenses/COPYING` 写明 GPL |
| 安装纯净性 | 2 | 未混入 `Makefile.am`/`configure`/`config.guess`/`etc`/`bin`/`rpm`/`devel`；`share/wm-icons` 下只有集合目录与 `names.lst` |

最有价值的两条是覆盖率断言：**图标集少一个"标准名"就是某一类语义图标在整个系统里
没有实现**（窗口管理器按语义名取图时会拿到空），而"目录里有 83 个文件"这种断言
完全发现不了；反过来，把"并集必须覆盖全部 84 个名字"固定下来，也能识别上游 tarball
被裁剪过。

## 两个踩过的点

1. `names.lst` 里的名字**不带扩展名**：各集合自行决定用 `.png` 还是 `.xpm`
   （`16x16-kde` 是 `.xpm`，`16x16-crystalclear` 是 `.png`）。所以比对时要把文件名
   去扩展名后再比，直接拿文件全名去比会 100% 误报。
2. `icons/` 下**每个集合都有一份自己的 `_symlinks.lst`**（31 份，其中 29 份非空），
   它们和 `names.lst` 不同层级，测试要分别断言。

## 构建与验证

纯资源包，本机即可跑完整门禁（不需要设备）：

```bash
source /home/silhouette/conanenv/bin/activate
export CONAN_HOME=/home/silhouette/.conan2-ohos
python3 scripts/ohc-run.py conan-verify wm-icons 0.4.0
```

## 来源

- Source URL: `https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/w/wm-icons/wm-icons_0.4.0.orig.tar.gz`
  （官方路径 `https://deb.debian.org/debian/pool/main/w/wm-icons/wm-icons_0.4.0.orig.tar.gz`）
- SHA256: `f0b85dee100cfcb53f0ea5a4d28d828edbf85986f76e980370bdd380f58e9690`
  （与 `wm-icons_0.4.0-11.2.dsc` 的 `Checksums-Sha256` 一致）
- License: GPL-2.0-or-later

---

**编译结束**: 2026-09-19
**最终状态**: built
