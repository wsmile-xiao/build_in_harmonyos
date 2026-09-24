# ZXCC

CP/M 2/3 模拟器与交叉开发工具链包装器

## 简介

zxcc（John Elliott）是一个运行在 Unix/Linux/鸿蒙PC 上的 CP/M 2/3 模拟器，
主要用途是在主机上直接运行 CP/M 侧的 Hi-Tech C 编译器以及 Digital
Research 的 MAC/RMAC/LINK/GENCOM 等汇编链接工具，从而把 CP/M 时代的
Z80/8080 软件开发流程搬进现代交叉开发环境。

- `zxcc`：CP/M BIOS/BDOS 模拟器驱动，加载 bios.bin 并运行 .com 工具
- `zxc` / `zxas` / `zxlink` / `zxlibr`：C 编译 / 汇编 / 链接 / 库工具入口
- 内嵌 CPMIO（控制台仿真）与 CPMREDIR（重定向文件系统）静态库

运行真正的编译需要用户自行安装 CP/M 侧的 Hi-Tech C 编译器文件到
`<prefix>/lib/cpm/{bin80,lib80,include80}/`。

## OHOS 适配要点

1. **config.guess/config.sub 无 HarmonyOS 支持**：补丁添加
   `*:HarmonyOS:*:*` 识别分支与 aarch64 / linux-ohos 三元组（无宏注入）。
2. **HMDFS + umask 077 权限怪癖**：configure 的 `umask 077 && mktemp -d`
   在 HMDFS 上生成属主权限位丢失的临时目录，补丁去除私有 umask。
3. **ncurses 依赖**：cpmio 控制台仿真需要 ncurses 头与 libncursesw，
   经 conan ncurses/6.5 依赖注入。

## 版本

- 0.5.7：首次适配（上游版本），published。
