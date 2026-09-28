# g810-led

Logitech RomerG / GX 机械键盘背光控制工具（G213 / G410 / G413 / G512 / G513 / G610 / G810 / G815 / G910 / GPro）。

- 上游：https://github.com/MatMoul/g810-led （GPL-3.0-only）
- 版本：0.4.3
- 构建系统：GNU makefile（C++ gnu++11），产物 `bin/g810-led`（CLI）+ `lib/libg810-led.so.0.4.3`（共享库）+ 公开头文件
- 依赖：hidapi（hidraw 后端，`-lhidapi-hidraw`）→ 传递依赖 libudev-zero（`-ludev`）

## OHOS 适配要点

1. makefile 的 `CPPFLAGS`/`LIBS` 为条件赋值、`CXXFLAGS` 使用 `?=`+`+=`：
   环境变量注入会被覆盖、命令行传 `CXXFLAGS` 会导致 `+=` 追加失效（丢失
   `-DVERSION`）。配方将 `CXX` 取自 Conan conf，`CPPFLAGS/LDFLAGS/LIBS`
   作为 make 命令行参数传入，`CXXFLAGS` 不传以保留 makefile 默认值。
2. 不使用官方 `install`/`setup` 目标（依赖 `udevadm`/`systemctl`，OHOS 不可用），
   `package()` 手工拷贝 `bin/`、`lib/`、公开头文件与示例配置。
3. 无上游测试（详见 notes.md 枚举台账）；新增消费者用例与鸿蒙专项测试。

## 测试

- 上游测试：0（官方 v0.4.3 无任何测试声明）
- 消费者用例：`test_package/consumer.cpp`（公开 API 编译/链接/运行）
- 鸿蒙专项测试：`test_ohos/run_ohos_test.py`（OHOS aarch64 上 4 项真实行为断言）
