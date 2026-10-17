# lsix

> Like `ls`, but for images: shows thumbnails of images directly in the
> terminal via SIXEL graphics.

- 上游: https://github.com/hackerb9/lsix
- 许可证: GPL-3.0-or-later
- 类型: 纯 bash 脚本 CLI 工具（单文件，无编译、无 ELF 产物）

## 在 HarmonyOS PC 上安装

```bash
conan install --requires=lsix/1.9.1 -pr:a=o
```

`lsix` 脚本安装到包内 `res/lsix`，通过 `#!/usr/bin/env bash` shebang 由系统
`bash`（或 Conan `bash/5.3` 包）解释执行。

## 运行要求

| 依赖 | 用途 |
|------|------|
| bash >= 4 | 解释器（上游 sanity check 强制 BASH_VERSINFO >= 3 且过滤 bash 3） |
| ImageMagick 7 (`magick`, `montage`) | 生成缩略图 montage 并编码为 SIXEL 流 |
| SIXEL 终端 | 真实显示（如 `xterm -ti vt340`）；无六角终端时仅输出错误 |
| `stty`（可选） | 终端 echo 切换与尺寸检测；HarmonyOS PC conanrun PATH 下通常缺失，补丁已使其可选 |

## 使用

```bash
lsix *.jpg              # 在当前目录中显示图片缩略图
lsix picture.png        # 显示单张图片
```

无参数时自动搜索当前目录的常见图片扩展名（jpg/jpeg/png/gif/webp/tiff/p?m/
xp[b]m/bmp/ico/svg/eps），动画 GIF 只取第一帧。

## 已验证的边界行为（无终端 CI 环境）

| 场景 | 观测契约 |
|------|----------|
| `--help` / 未知参数 | 当作文件名传给 ImageMagick；rc=0、stdout 空、stderr 非空、不挂起 |
| 无 ImageMagick | rc=1、stdout 空、stderr 含 `Please install ImageMagick` |
| 无 sixel 终端 | rc=0（trap 覆盖 exit 1）、stdout 恰 2 字节 `\e\\`、stderr 含报错 |
| `LSIX_FORCE_SIXEL_SUPPORT=1` | 完整 montage→convert→sixel 管线照常运行（无需 tty 应答） |
| 双图 montage | 调色板 #0 红 / #1 蓝 / #2 白（标签），几何 ~756x126 |

## 已知限制（CI 不可验证，需真实终端）

- SIXEL 图形的实际渲染效果
- 终端前景/背景色、调色板大小、六角几何的自检测应答
- `stty -echo`/`stty echo` 的终端状态切换
- 脚本末尾等待终端应答的 `read -s -t 60`（真实终端下的收尾行为）

这些边界在 `1.9.1/notes.md` 中有详细记录。
