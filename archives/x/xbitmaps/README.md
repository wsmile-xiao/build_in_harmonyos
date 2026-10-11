# xbitmaps — X11 位图数据包

`xbitmaps` 提供 X11 客户端使用的 71 个位图数据文件（1x1、boxes、target、
xlogo16、mensetmanus 等）。每个文件是 XBM 形态的 C 源码：`#define
<name>_width/_height` + `static char <name>_bits[]`，安装到
`include/X11/bitmaps/`，由消费程序 `#include` 或按 X11 位图格式解析。

## OHOS 适配要点

- **纯数据包**：上游 autotools 只做数据安装，零编译、零链接、零三方依赖、零补丁。
- **数据完整性即验证**：`build()` 对全部 71 个文件做 X11 打包规则校验
  （`((width+7)/8)*height == bits 字节数`）。
- 官方源用 `xorg.freedesktop.org` 形式 URL（CI 镜像链可接管，国内直连 www.x.org 常失败）。

## 产物

| 路径 | 说明 |
|------|------|
| `include/X11/bitmaps/*` | 71 个 XBM 位图数据文件 |

## 参考资料

- 上游仓库：<https://gitlab.freedesktop.org/xorg/data/xbitmaps>
- 许可证：MIT
