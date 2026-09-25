# blendsel

Debian Pure Blends 安装选择器（`tasksel` 的 fork，Debian Install System
Team 维护）——纯 Perl CLI 工具，用于选择安装 Debian blends（Debian Astro/
Med/Junior/Science/Hamradio/FreedomBox 等）。

Homepage: https://salsa.debian.org/installer-team/blendsel

## OHOS 适配

- **纯脚本包**（Debian native 源包，无 C/C++）：以 conan `perl/5.42.2`
  为运行时依赖直接打包交付（蓝本：`abcselect/1.5` 纯 Perl 脚本包先例）
- 补丁 `patches/0001`：env shebang（OHOS 无 `/usr/bin/perl`）、
  `Locale::gettext` 可选加载 + 英文回退（Debian XS 模块，core perl 无）、
  数据路径随 `$0` 前缀推导（Debian `/usr` 布局不变，自定义 prefix 下
  relocation-free）
- `debian-tasks.desc` 任务描述数据由 `makedesc.pl`（纯 perl）构建期生成，
  man 页由 perl 自带 `pod2man` 生成

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| perl | 5.42.2 | 运行时解释器（ohpcd 预编译 OHOS arm64 制品） |

## 验证边界（OHOS 生态）

install/remove 与 debconf UI 路径依赖 Debian 的 apt-get/dpkg/debconf
生态（OHOS 无），如实记录不可运行；纯 Perl 数据链
（`--task-packages`/`--task-desc`/usage）已由 test_package 冒烟验证。

## Versions

| Version | Status |
| --- | --- |
| 0.11 | built |

## 功能验证

```bash
# 任务 Key 包查询（数据链）
blendsel --task-packages=med-blend
# -> task-med-blend
# 未知选项打印用法
blendsel --help
```

License: GPL-2.0-or-later
