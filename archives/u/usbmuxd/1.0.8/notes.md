# usbmuxd 1.0.8 notes

## Scope

iPhone/iPod Touch USB 多路复用守护进程（libimobiledevice 生态服务端）。
交付物：`sbin/usbmuxd` 守护进程 + `bin/iproxy` 端口转发工具。
任务 #13997，taskBranch=feat/usbmuxd-1.0.8。

## Upstream shape (v1.0.8 tag, 2012)

- 老式 CMake 2.6 构建（`PROJECT(usbmuxd)` + Modules/ 自带 Find 模块）。
- `daemon/`：usbmuxd 守护进程（main.c/usb-linux.c/client.c/device.c/log.c
  + common/utils.c），libusb-1.0 后端 + libplist（协议 v1，plist 序列化）。
- `libusbmuxd/`：内嵌老版客户端共享库（soname usbmuxd.so.2，API 与独立
  libusbmuxd 包同源但更老）。
- `tools/iproxy.c`：端口转发工具，链接内嵌库 + sock_stuff 私有帮助函数。
- `udev/`：Linux udev 规则。
- 无测试：无 tests/、无 add_test()、无 make check 目标（N=0）。

## Adaptations（patches/0001-ohos-cmake-standalone-libusbmuxd.patch）

1. **cmake_minimum_required 2.6→3.5**：CMake 4.x 移除 <3.5 兼容（配
   `CMAKE_POLICY_VERSION_MINIMUM=3.5` 双保险）。
2. **内嵌 libusbmuxd 库不构建**：制品仓已有独立 libusbmuxd/2.0.2；
   内嵌老版 `libusbmuxd.c` 的 `usbmuxd_unsubscribe()` 调用
   `pthread_cancel()`——OHOS musl sysroot 无该符号声明（E085：musl 不
   实现 POSIX 线程取消；设备 libc 导出但 sysroot 头缺失，见
   DRAFT-ohos-pthread-cancel-decl），链接失败。守护进程本体
   （daemon/*.c）不使用 pthread_cancel，无需处理。
3. **iproxy 改链制品仓 libusbmuxd-2.0**：`USBMUXD_INCLUDE_DIRS`/
   `USBMUXD_LIBRARIES` 由配方注入；其私有 sock_stuff 三函数
   （create_socket/recv_buf_timeout/send_buf）从源码树直接编入
   iproxy（独立库不导出）。iproxy 传递链接 libplist（OPT_LIBS）。
4. **daemon/client.c `plist_dict_insert_item`→`plist_dict_set_item`**：
   libplist 2.7.0 API 更名（12 处；libimobiledevice-glue 同款先例）。
5. **iproxy.c handle 打印 `%d`→`%u`**：独立库 usbmuxd_device_info_t.handle
   是 uint32_t。
6. **FindUSB/FindPLIST 注入**：老式 LibFindMacros 走 host pkg-config，
   交叉环境探测不到 sysroot；配方直接注入 cache 变量
   （USB_INCLUDE_DIR/USB_LIBRARY/PLIST_INCLUDE_DIR/PLIST_LIBRARY）。
7. **udev 仅 Linux 安装**：`CMAKE_SYSTEM_NAME MATCHES "Linux"` 分支
   保留原样（OHOS 不命中）。

## Verification

本机 conan create（ohos-aarch64，clang 15，Release）——见 .ci-result.json。

- 上游测试：N=0（上游 2012 年代无测试框架；守护进程运行时路径需要
  iOS 设备 + USB 直通，CI 环境不可得）。
- 消费者测试（test_package，3/3 断言）：
  1. `usbmuxd -h` 打印 usage banner（含 --force-exit 选项）退出 0
     （ELF 加载 + getopt_long + libc printf，在任何 socket/USB 工作
     之前执行的完整用户态路径）。
  2. `iproxy`（无参）打印 `LOCAL_TCP_PORT DEVICE_TCP_PORT` usage 退出 0
     （libusbmuxd-2.0 客户端链接 + sock_stuff 编入验证）。
  3. 消费者 C 程序（链接 libusbmuxd）：无守护进程时
     `usbmuxd_get_device_list()`/`usbmuxd_connect()` 返回负错误码
     （-ENODEV 路径，不崩溃）+ `usbmuxd_device_list_free(NULL)` 安全。
- 手工探索构建记录：daemon + iproxy 链接成功，`usbmuxd -h` /
  `iproxy` 无参 usage 实测输出正常（LD_LIBRARY_PATH 带上 libusb 包
  lib 目录后）。

## Notes

- 上游 v1.0.8 无 release tarball（releases/download/1.0.8/ 404），
  conandata.yml 用 codeload 官方 tag 归档（R39 官方源口径）。
- commands.json type=tool（kfourinline #11104 先例：type=app 被 L0k
  拦截，工具/守护进程型必须 "tool"）。
- 版本策略：1.0.8 为上游 tag v1.0.8 的精确版本号。
