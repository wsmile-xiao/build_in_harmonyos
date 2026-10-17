# xclip

> X11 剪贴板命令行工具（读写 X selections / clipboard）

## 简介

xclip 是一个在 X11 环境下访问剪贴板（selections: primary/secondary/clipboard）
的命令行工具，支持通过管道输入/输出文本。xapers（参考文献管理工具）依赖
xclip 实现选定文本的复制与粘贴。

本归档版本为 **0.13.1**（上游 tag 0.13 的适配修复版本，R37）。
0.13 已由 PR1470 合并到 main（status=built）但从未发布到制品仓；
0.13.1 修复源码 URL（原 savannah 已 404）、Xresource.h 头文件缺失等问题，
待 PR 合并后由 release 流水线发布到制品仓，供下游（xapers-0.9.0）以 conan 依赖引用。

## OHOS 适配要点

1. **X11 库为 conan 依赖**（libx11/6.4.0、libiconv/1.17 从制品仓拉取，传递依赖
   xorgproto/2025.1、libxcb/1.16），configure 通过 `--x-includes/--x-libraries`
   指向 conan 包路径，CI worker 无需本机预编译 X11。
2. **libXmu/libXt stub**：configure.ac 检测 `X11/Xmu/Atoms.h` 和 `X11/Intrinsic.h`
   及 `XmuClientWindow`，但 xclip 实际未调用，用最小 stub 头文件 + stub libXmu.a 满足检测。
3. **Xresource.h**：新版 libX11 (6.4.0) 将 Xrm 类型移入独立头文件，xclip.c 需补 include
   （见 patches/0001-xclip.c.patch）。
4. **运行时依赖 libxcb.so.1**：libX11 6.4.0 基于 XCB 传输层，目标系统需提供 libxcb。
5. **E011**：HMDFS 上 config.status 临时目录因 `umask 077` 不可写，build() 中 sed 为 022。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libx11 | 6.4.0 | conan 依赖（X11 核心库，含 XCB 传输层） |
| libiconv | 1.17 | conan 依赖 |
| xorgproto | 2025.1 | conan 传递依赖（X11 协议头） |
| libxcb | 1.16 | conan 传递依赖（libX11 运行时传输层） |

## 功能验证

```bash
# 版本输出（无需 X server）
xclip -version

# 剪贴板读写（需 X server）
echo "hello" | xclip -selection clipboard
xclip -selection clipboard -o
```

## 参考

- 上游仓库: https://github.com/astrand/xclip
- 制品仓引用: `xclip/0.13.1`（conan requires）
