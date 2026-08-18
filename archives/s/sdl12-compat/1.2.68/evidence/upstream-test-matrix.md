# sdl12-compat 1.2.68 上游测试矩阵

## 统计口径

上游 `release-1.2.68` 的 `test/` 目录包含 32 个独立 C 测试程序。上游 CMake 构建全部 32 个程序，但未注册 CTest。当前配方显式执行适合无人值守 HarmonyOS PC 环境的程序，任何非零退出都会使 `conan create` 失败。

| 指标 | 结果 |
|---|---|
| 上游程序总数 | 32 |
| 编译成功 | 32/32 |
| 无人值守执行 | 14/32 |
| 已执行程序通过率 | 14/14（100%） |
| 未执行 | 18/32（逐项说明设备或交互限制） |

## 已执行的 14 个上游程序

运行环境统一设置 `SDL_VIDEODRIVER=dummy` 和 `SDL_AUDIODRIVER=dummy`。

| 测试 | 固定命令/参数 | 覆盖 | 结果 |
|---|---|---|---|
| `testver` | `./testver` | 编译时和运行时 SDL 1.2 版本 | PASS |
| `testplatform` | `./testplatform` | 平台、字节序、CPU 和基础数据类型 | PASS |
| `testerror` | `./testerror` | 多线程错误状态 | PASS |
| `testiconv` | `./testiconv` | 字符编码转换 smoke/stress | PASS（exit 0） |
| `testfile` | `./testfile` | RWops 创建、读写、seek、append 及错误路径 | PASS（test1–test5） |
| `testkeys` | `./testkeys` | SDL 1.2 keysym 名称表 | PASS |
| `testloadso` | `./testloadso --hello libc.so` | 动态加载、解析并调用 `puts` | PASS |
| `torturethread` | `./torturethread` | 10×10 线程创建、同步和销毁 | PASS |
| `testvidinfo` | `./testvidinfo` | dummy 视频驱动和显示格式查询 | PASS |
| `testblitspeed` | `./testblitspeed --seconds 1` | BMP 加载、surface 转换和软件 blit | PASS |
| `testsem` | `./testsem 2` | 10 线程 semaphore 竞争和超时 | PASS |
| `testthread` | `./testthread` | 线程创建、等待、kill 兼容和 signal 路径 | PASS |
| `testtimer` | `./testtimer 10` | 单 timer、多 timer、移除和错误路径 | PASS |
| `testjoystick` | `./testjoystick` | 摇杆子系统初始化和设备枚举 | PASS（当前 0 设备） |

## 未执行的 18 个上游程序

这些程序均完成编译，但不把“编译成功”“被 timeout 杀死”或“缺少硬件后端”计作测试通过。

| 测试 | 未执行的具体原因 |
|---|---|
| `checkkeys` | 创建窗口后无限等待真实键盘/退出事件 |
| `graywin` | 窗口渐变演示，等待键鼠或窗口退出事件 |
| `testalpha` | 交互式窗口和鼠标绘制，循环等待人工退出 |
| `testbitmap` | 显示位图后等待键鼠或窗口退出事件 |
| `testcursor` | 自定义光标测试，需要真实鼠标移动和人工退出 |
| `testoverlay` | 视频 overlay 交互显示，需要窗口事件退出 |
| `testoverlay2` | overlay 播放主循环等待退出或 resize |
| `testpalette` | palette 动画依赖人工事件触发 fade-out |
| `testsprite` | sprite 动画主循环等待键盘/窗口退出 |
| `testwin` | 多色深窗口/BMP 显示，等待人工事件 |
| `testwm` | 窗口管理器标题、图标、键鼠和 syswm 交互 |
| `threadwin` | 多线程窗口事件处理，等待人工输入退出 |
| `loopwave` | 循环播放 WAV，需要真实音频行为和信号/人工终止 |
| `testcdrom` | 需要物理 CD-ROM 设备、介质和控制操作 |
| `testdyngl` | 需要 OpenGL/GPU 上下文，渲染循环等待键盘事件 |
| `testgl` | 需要 OpenGL/GPU 上下文，渲染循环等待人工退出 |
| `testgamma` | 需要真实显示 gamma/ramp；dummy 后端实测返回不支持 |
| `testlock` | 无限 mutex/signal 压力循环，只能由外部信号结束，无法以正常退出码判定通过 |

## 消费者测试

Conan `test_package` 真实链接 `SDL::SDL`，通过 `/proc/self/maps` 验证加载包内 `libSDL2-2.0.so.0`，并覆盖版本、dummy surface、颜色填充、flip、事件 round trip、timer/delay 和正常退出。结果为 1/1 通过，内部 9 项断言全部通过。
