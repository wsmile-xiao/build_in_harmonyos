# DRAFT-14966-libusb-1.0.29-sandbox-usb-device-discovery-block

## 问题

libusb（及一切 libusb 系 USB 访问库）在 OHOS HAP 应用沙箱里，默认初始化
`libusb_init()` 无条件走 Linux 后端的设备发现路径——枚举
`/sys/bus/usb/devices/`（sysfs）+ 打开内核 netlink socket（kobject_uevent，
热插拔）。这两条路径在鸿蒙 SELinux 策略下都是 **neverallow 硬性禁止**：

```
$ ls /sys/bus/usb/devices/
ls: /sys/bus/usb/devices/: Permission denied        # errno=13
```

后果链：

- `libusb_init(NULL)` 返回 -1（LIBUSB_ERROR_IO），任何设备操作之前就死
- 上游 4 个测试程序（stress/stress_mt/set_option/init_context）全部调用默认
  初始化，`--enable-tests-build` 实测 **0/4 全灭**：

```
FAIL: stress        — Failed to init libusb on iteration 0: -1
FAIL: stress_mt     — Thread 0..7 failed (iteration 0): LIBUSB_ERROR_IO
FAIL: set_option    — 同上，libusb_init 失败
FAIL: init_context  — 同上
# TOTAL: 4 / PASS: 0 / FAIL: 4
```

## 根因

**平台策略边界，非代码缺陷**。库本身可编译、可链接、API 面可用；被阻断的是
沙箱域（hishell_hap 等 HAP 域）对 USB 子系统的访问：

```cil
(allow hishell_hap sysfs (dir (search)))                        # 未授予
(neverallowx hap_domain dev_bus_usb_file (ioctl chr_file ...))  # ioctl 区间禁
(neverallow hap_domain domain (netlink_kobject_uevent_socket (write append)))
```

允许触 USB 的域是系统服务（udevd/hdf_ext_devmgr/sane_service/scan_service），
不是 HAP 沙箱。该限制跨 libusb 1.0.24..1.0.29 版本不变（Linux 后端无结构
变化），1.0.29（2026-10-08）复测签名一致。

## 修复（两件套）

### 1. 消费/测试初始化路径（代码层）

用显式 context 退出设备发现：

```c
const struct libusb_init_option options[] = {
    { LIBUSB_OPTION_NO_DEVICE_DISCOVERY, { .ival = 1 } },
};
libusb_context *ctx = NULL;
int rc = libusb_init_context(&ctx, options, 1);
```

⚠️ **`.ival` 必须传 1 而非 0**——传 0 等价默认行为，仍走被阻断的 sysfs
路径（1.0.27.1 分支真实 AI review P2 发现，commit 2688668e94）。
`archives/l/libusb/1.0.29/test_package/test_libusb.c` 以此形态作为平台
初始化断言（真机 5/5 通过）。

### 2. 上游测试统计口径（申报层）

- **不开** tests-build（上游默认 no，tests/ 不进 SUBDIRS，make check 无失败项）
- **不虚报** 4/4——上游注册口径 N=4，每项带平台关键词逐项豁免：
  `环境限制: OHOS HAP 沙箱 SELinux neverallow 阻断 sysfs/netlink 设备发现
  （报错定位: Failed to init libusb on iteration 0: -1 (LIBUSB_ERROR_IO)）`
- 证据包：本地以 `--enable-tests-build` 跑一次 0/4 留证进 notes.md +
  宿主探测 `ls /sys/bus/usb/devices/ → Permission denied`；
  NO_DEVICE_DISCOVERY 消费冒烟是真实运行验证载体

## 降级方案

- 若未来 OHOS 策略授予沙箱只读 sysfs USB 树：重开 tests-build 报真实数字
- 无 USB 栈的 worker 环境（容器）：NO_DEVICE_DISCOVERY 冒烟仍验证
  链接 + API + context 生命周期
- 真需要设备 I/O 的应用：走 USB Manager NDK API（usb_usb_manager），
  而非 libusb sysfs 枚举（1.0.27 归档能力评估含完整 neverallow CIL 分析）

## 适用范围

libusb、libusbsio、rtl-sdr、libdfu-ahp、libam7xxx、sispmctl、knxd、
pcsclite（USB 读卡器）等一切 libusb 依赖包；任何 build() 里跑
`make check` 且测试二进制调用默认 `libusb_init()` 的配方。

## 验证

- libusb/1.0.29 本地 conan create -pr=ohos-aarch64 RC=0
  （make check 无失败项 + test_package 5/5，2026-10-08）
- --enable-tests-build 探针轮 4x FAIL LIBUSB_ERROR_IO（notes.md §4 留证）
- 消费冒烟实测输出 `libusb consumer smoke passed: 1.0.29`
