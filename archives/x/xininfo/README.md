# xininfo

X11 多显示器布局信息查询命令行工具：打印当前桌面总尺寸、显示器数量与每块显示器的
位置/尺寸、活动显示器序号、活动显示器名等，供 shell 脚本按显示器几何做窗口摆放。

## 功能

- 读取 Xrandr（输出名/连接状态）+ Xinerama（逻辑显示器布局）两套信息并合并
- 输出总量：`-total-width` / `-total-height`
- 按活动或指定显示器（`-monitor N`）输出 `-geometry` / `-width` / `-height` / `-x` / `-y` / `-name` / `-active-mon`
- `-h` / `-help` 通过 `man` 打开自带手册页

## 编译版本

- **0.14.11** (2026-09-25): HarmonyOS PC 适配版本

## OHOS 适配

- 上游只有裸 `Makefile`（无 configure/autotools/cmake），配方不改上游构建文件，
  用命令行变量 `BUILD_DIR`/`PREFIX` 覆盖完成隔离构建与手册页路径烧录
- 上游 `make install` 在本平台不可用（依赖 `md2man-roff` 与 `install(1)`，设备 PATH 均无），
  由配方 `package()` 显式落盘 `bin/xininfo`、`share/man/man1/xininfo.1`、`licenses/LICENSE`
- X11 依赖（libx11 / libxrandr / libxinerama）全部走 Conan 制品仓，头文件与库经
  `pkg-config`（上游 Makefile 原生使用）解析
- 产物 ELF 经 `binary-sign-tool` 自签（E077），否则鸿蒙内核拒绝执行
- 上游无自动化测试套件；OHOS 侧无 X server，功能测试不可执行，消费者测试以
  确定性断言覆盖"可执行 + 链接 + 上游错误代码路径 + 产物完整性"（详见版本目录 notes.md）

## 依赖

- libx11/6.4.0、libxrandr/1.5.5、libxinerama/1.1.6（Conan 制品仓 ohpcd）

## 参考资料

- 上游仓库: https://github.com/DaveDavenport/xininfo
