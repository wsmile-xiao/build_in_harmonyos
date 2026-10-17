# E429 — OHOS 受限 `/dev/bus` 下 `libusb_init()` 失败 + 未检查返回值 → NULL context SIGSEGV

- 状态: 草稿（贡献者 FBD7）
- 首次发现: xfel 1.3.5 适配（2026-10-03）
- 严重度: 🟡 2（medium）
- 分类: platform, ohos, limitation, compat, portability

## 错误特征

程序启动即段错误，**没有任何诊断输出**：

```
$ ./xfel version
$ echo $?
139            # 128 + 11 = SIGSEGV
```

用 `LIBUSB_DEBUG=4` 运行可见 libusb 内部失败点：

```
[libusb: debug] [get_kernel_version] HongMeng/OHOS kernel detected (HongMeng Kernel 1.12.0), assuming modern Linux kernel
[libusb: debug] [op_init] found usbfs at /dev/bus/usb
[libusb: debug] [op_init] sysfs is available
[libusb: error] [sysfs_get_device_list] opendir devices failed, errno=13
libusb_init r=-1 ctx=0
```

`error_signature`: `Can't initialize libusb|libusb_init.*r=-1|sysfs_get_device_list.*errno=13|libusb_get_device_list.*NULL`

## 触发条件

- 触发工具: `runtime`
- 阶段: `runtime`（进程启动、设备枚举前）
- 环境: OHOS/HarmonyOS 沙箱、容器、CI——凡是无 USB 设备节点访问权限
  （`/dev/bus` / `/sys/bus/usb/devices` 不可读）的场合
- 代码形态: 调用 `libusb_init(&ctx)` **不检查返回值**，随后把 `ctx` 交给
  `libusb_get_device_list(ctx, &list)` 等 API

## 根因分析

1. `libusb_init()` 在该环境下返回 **-1**（`LIBUSB_ERROR_IO`），且 `ctx` 保持 `NULL`。
   直接原因不是内核不识别——libusb 1.0.27 **已识别** HongMeng/OHOS 内核——而是
   `sysfs_get_device_list` 打不开 `/sys/bus/usb/devices`，`errno=13`（EACCES）。
2. 上层代码忽略返回值，继续以 `NULL` 作 context 调用 `libusb_get_device_list()`；
   libusb 在解析默认 context（此时不存在）时解引用空指针 → SIGSEGV。
3. 因为崩溃发生在任何 `printf` 之前，表现为"无输出的 139"，极易被误判为随机失败。

## 解决方案

### 推荐方案（priority 1）

调用 `libusb_init()` 后**必须检查返回值**，非 0 时打印可读错误并退出：

```c
if(libusb_init(&context) != 0)
{
    printf("ERROR: Can't initialize libusb\r\n");
    return -1;
}
int count = libusb_get_device_list(context, &list);
```

修复后同类命令退化为可预期结果：`rc=255` + `ERROR: Can't initialize libusb`
（对应 xfel 的 `patches/0001-main.c.patch`）。

### 回退/诊断方案（priority 2）

用 `LIBUSB_DEBUG=4` 定位失败点，确认是**环境权限**而非工具链问题：

```bash
LIBUSB_DEBUG=4 ./tool 2>&1 | grep -E "libusb_init|sysfs_get_device_list|errno"
```

### 禁止做法

- ❌ 忽略 `libusb_init()` 返回值，继续把可能为 `NULL` 的 context 传给
  `libusb_get_device_list()` / `libusb_exit()` 等 API
  后果: 进程崩溃且无诊断输出（rc=139），CI/test_package 误判为随机失败
- ❌ 用 `LD_LIBRARY_PATH`/RPATH 方向排查——本问题与库定位无关

## 验证

```bash
# 修复前: rc=139（无输出）
./tool <subcommand> ; echo $?
# 修复后: rc=255 + ERROR 行
./tool <subcommand> ; echo $?
```

## 关联条目

- 同族: E212（HNP/hmmac 相关沙箱限制）、E077（ELF 签名）
- 参考实现: `archives/x/xfel/1.3.5/patches/0001-main.c.patch`
