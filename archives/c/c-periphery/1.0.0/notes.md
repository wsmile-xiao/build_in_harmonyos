# c-periphery 1.0.0 适配笔记

## 编译环境
- 构建系统: 原生 GNU Makefile（v1.0.0 无 CMakeLists.txt）
- 编译日期: 2026-08-30
- 编译器: clang 15.0.4 (target aarch64-unknown-linux-ohos)，ar=llvm-ar
- 状态: built（本机预检通过；权威 CI 待运行）

## 编译步骤

1. 下载源码（conandata.yml，codeload 链路，SHA-256 复测一致）
2. 应用补丁：patches/0001-ohos-termios-speed.patch
3. make CC=clang AR=llvm-ar -j1 → periphery.a
4. make CC=clang AR=llvm-ar tests -j1 → 仅编译 5 个上游测试二进制（不运行）
5. 无 install 目标：package() 拷贝 periphery.a 到 lib/ 并改名为 libperiphery.a
   （CMake find_library 默认 lib 前缀），src/*.h 到 include/

## 构建约束（如实记录）

- 纯 Makefile，无 configure/autotools/CMake
- 仅静态库 periphery.a（-fPIC 已含于上游 CFLAGS）；无 shared 目标
- 无 install/shared/check 目标；make tests 只编译 5 个测试程序，不运行
- 零外部依赖：libc + linux/i2c.h、linux/i2c-dev.h、linux/spi/spidev.h（sysroot 实存）
- 运行期需要真实外设节点：/sys/class/gpio（gpio）、/dev/i2c-*（i2c）、
  /dev/mem（mmio）、/dev/tty*（serial）、/dev/spidev*（spi）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | src/serial.c 编译失败：no member named c_ispeed/c_ospeed in struct termios（10 处） | OHOS NDK bits/termios.h 将输入/输出波特率成员声明为 __c_ispeed/__c_ospeed（双下划线前缀），与 POSIX 命名不一致 | 补丁 0001-ohos-termios-speed.patch 改走 POSIX 抽象 API（cfsetispeed/cfsetospeed 设置、cfgetospeed 读取），不直接命名波特率成员、不引入任何平台条件编译宏（R8 合规，round-4 官方 bot 指出后按建议整改）；非标准波特率（128000/135000 等，sysroot 无对应 B 常量）显式返回 SERIAL_ERROR_CONFIGURE，较上游更安全的降级，详见补丁说明 |

## 补丁说明

- patches/0001-ohos-termios-speed.patch（唯一补丁，portability）
- R8 合规：补丁**零平台条件编译宏**（__OHOS__/__musl__/__linux__/__APPLE__ 等一律不出现，
  同一份代码全平台生效），通过 POSIX 抽象 API 适配——不直接命名 struct termios 的
  波特率成员（OHOS NDK 为 __c_ispeed/__c_ospeed，与 POSIX c_ispeed/c_ospeed 不同）。
- 波特率设置改走 cfsetispeed()/cfsetospeed()（标准波特率自动同时写 c_cflag 的 B* 位与
  ispeed/ospeed 成员，全平台语义一致）；读取路径改走 cfgetospeed()。
- custom speed 处理（实测降级，如实记录）：OHOS NDK sysroot 无 B128000/B135000 等常量，
  cfsetispeed 对非标准速率实测返回 -1（拒绝，成员不变）；无任何无平台宏路径可写入
  __c_ispeed/__c_ospeed。故非标准波特率（128000/135000 等 _serial_baudrate_to_bits 映射
  失败的值）改为**显式错误**：serial_open/serial_open_advanced 返回
  SERIAL_ERROR_CONFIGURE（-6，errmsg 说明 not a standard rate，open 失败分支同步
  close+fd=-1，serial_close 安全），serial_set_baudrate 返回 SERIAL_ERROR_CONFIGURE 且
  端口保持旧波特率不变——较上游「写入成员+BOTHER 后 tcsetattr 结果未检查」的行为更安全
  （上游 custom 值在 OHOS 上本就无效且报错语义缺失）。标准波特率 50..4000000 全 30 档
  经设备实测 cfset*/tcsetattr/读回 100% 生效（probe 30/30）。
- 最小性：5 个 hunk，全部位于 serial.c 波特率设置/读取路径（+24/-18 行），不改上游其余逻辑
- 双验证：conan patch_ng（apply_conandata_patches 实际调用的 patch() 实现，干净解包）
  + git apply --check 均通过。系统 toybox patch 0.8.12 对**本补丁**（git 风格头）实测可
  正常应用（pristine e6b0763e…→6a6ab5b0…，--dry-run 与实打均 rc=0）；round-1~3 记录
  的「toybox patch 静默 no-op」现象针对当时补丁未复现，不再作为依赖项声明

## 上游测试（如实披露，未运行）

- 官方入口 make tests：只编译 5 个测试（test_gpio/i2c/mmio/serial/spi），不运行
- 本机实测（clang 交叉编译）：make all + make tests 全部编译成功（5/5）
- 5 个测试逐一实测运行结果（无硬件 OHOS 构建机）：
  - test_gpio（38 39，stdin 管道 y）：assertion failed at test_open_config_close:40（/sys/class/gpio 导出失败，无 root 权限）
  - test_i2c：usage 后退出 1；有参运行时 open(/dev/i2c-*) = ENOENT
  - test_mmio：明确假设 BeagleBone Black；mmio_open 后断言失败（无 /dev/mem）
  - test_serial：open(/dev/tty*) = ENOENT/EACCES
  - test_spi：open(/dev/spidev*) = ENOENT
- 结论：上游 5/5 测试 100% 依赖真实硬件 + 交互 stdin（getc），属环境限制而非依赖缺失；
  本 run 按上游测试门禁进入 AWAITING_USER_TEST_DECISION，不做任何 skip/伪造
- 官方 CI 对照：master build.yml 仅执行 make all tests（编译，从不运行测试二进制）

## 验证结果（本机预检，非权威 CI）

- make all：periphery.a 生成（51522 字节，ar rcs）
- make tests：5 个测试可执行文件全部生成
- 错误路径探针（真实链接 + 调用）：
  - gpio_open 非法方向 → -1 (GPIO_ERROR_ARG) + errmsg 正确
  - i2c_open(/dev/i2c-9) → -2 (I2C_ERROR_OPEN) + errno=ENOENT
  - serial_open(/dev/ttyPROBE) → -2 (SERIAL_ERROR_OPEN) + errno=ENOENT
  - mmio_open(0x44e10000) → -2 (MMIO_ERROR_OPEN，无 /dev/mem)
- test_package 断言集与上述实测行为一致

## 交付物

- 静态库 periphery.a + 5 个头文件（gpio.h/i2c.h/mmio.h/serial.h/spi.h）+ LICENSE
- 无 bin/ 产物（纯库）

---
**编译结束**: 2026-08-30（本机预检）
**最终状态**: built（待权威 CI + 用户测试决策）
