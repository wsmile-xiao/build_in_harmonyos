# libpciaccess 0.19 测试报告

## 测试环境

- 平台：HarmonyOS PC arm64
- 编译器：Clang 15.0.4
- 构建系统：Meson 1.11.1 / Ninja 1.13.1
- 源码：X.Org 官方 `libpciaccess-0.19.tar.xz`

## 上游测试

执行命令：

```bash
meson test -C builddir --print-errorlogs
```

实际输出为 `No tests defined.`。对官方源码包进一步清点：名称包含 `test` 的目录为 0、名称包含 `test` 的文件为 0；根目录、`src/`、`scanpci/`、`man/` 下全部 4 个 `meson.build` 中 `test()` 注册为 0。因此上游 0.19 测试用例总数为 **0**，执行结果记为 **0/0**；没有修改、删除或跳过上游测试。

## 新增消费者测试

消费者测试 `test_package/test.c` 始终调用 `pci_get_strings()` 验证无需硬件权限的名称查询契约，并调用 `pci_system_init()`。在允许访问 PCI sysfs 时，测试继续调用：

- `pci_system_init()`
- `pci_slot_match_iterator_create()`
- `pci_device_next()`
- `pci_device_is_boot_display()`
- `pci_iterator_destroy()`
- `pci_system_cleanup()`

在允许访问 PCI sysfs 时，测试遍历设备并完成清理；在沙箱拒绝 PCI sysfs 访问时，仅接受 `EACCES`、`ENOENT` 或 `ENOSYS` 这三类预期平台结果，其他错误均失败。

探索阶段执行结果：

```text
libpciaccess consumer test: name lookup passed; platform access unavailable (13)
```

消费者测试：**1/1 通过**。

### 鸿蒙特有测试

新增 `test_package/harmonyos_platform.c`，在实际链接的 `libpciaccess` 消费者中验证 HarmonyOS 平台路径：

- 调用 `pci_get_strings()` 验证通配 PCI 查询不返回伪造名称；
- 调用 `pci_system_init()` 验证 HarmonyOS PCI 后端；
- 真实设备访问可用时执行清理；
- 沙箱受限时仅接受 `EACCES`、`ENOENT` 或 `ENOSYS`。

探索阶段输出：

```text
libpciaccess HarmonyOS platform test: restricted PCI access accepted (13)
```

鸿蒙特有测试：**1/1 通过**。

## 构建与安装验证

应用 HarmonyOS Meson 平台识别修复后，库和工具均成功编译；探索安装包含：

- `lib/libpciaccess.so.0.11.1`
- `include/pciaccess.h`
- `lib/pkgconfig/pciaccess.pc`
- `bin/scanpci`

Conan 配方仅打包库、头文件和 pkg-config 元数据，关闭 `install-scanpci`，因此无需 `commands.json`。

## 汇总

| 测试类型 | 用例数 | 通过 | 失败 |
|----------|-------:|-----:|-----:|
| 上游测试 | 0 | 0 | 0 |
| 新增消费者测试 | 1 | 1 | 0 |
| 鸿蒙特有测试 | 1 | 1 | 0 |
| 合计 | 2 | 2 | 0 |
