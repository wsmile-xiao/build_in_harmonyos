# libpciaccess 0.17 测试报告

## 测试环境

- 平台：HarmonyOS PC arm64（本地 conan create + W3 本地 CI 模拟，与 CI 同 profile：ohos-aarch64 / clang 15）
- 编译器：Clang 15.0.4
- 构建系统：Meson 1.11.1 / Ninja 1.13.1
- 源码：X.Org 官方 `libpciaccess-0.17.tar.xz`（sha256 `74283ba3...95b73`）

## 上游测试

执行命令：

```bash
meson test -C builddir --print-errorlogs
```

实际输出为 `No tests defined.`。对官方源码包进一步清点：名称包含 `test` 的目录为 0；根目录、`src/`、`scanpci/`、`man/` 下全部 `meson.build` 中 `test()` 注册为 0。因此上游 0.17 测试用例总数为 **0**，执行结果记为 **0/0**；没有修改、删除或跳过上游测试。

## 新增消费者测试

消费者测试 `test_package/test.c` 调用 `pci_get_strings()`（走 zlib 支撑的 pci.ids 名称查询路径）验证无需硬件权限的名称查询契约，并调用 `pci_system_init()`。在允许访问 PCI sysfs 时，测试继续调用：

- `pci_system_init()`
- `pci_slot_match_iterator_create()`
- `pci_device_next()`
- `pci_iterator_destroy()`
- `pci_system_cleanup()`

沙箱拒绝 PCI sysfs 访问时，仅接受 `EACCES`、`ENOENT` 或 `ENOSYS` 这三类预期平台结果，其他错误均判失败。

本地 W3 执行结果：

```text
libpciaccess consumer test: name lookup passed; platform access unavailable (13)
```

消费者测试：**1/1 通过**。

### 鸿蒙特有测试

新增 `test_package/harmonyos_platform.c`，在实际链接 `libpciaccess` 的消费者中验证 HarmonyOS 平台路径：

- 调用 `pci_get_strings()` 验证通配 PCI 查询不返回伪造名称；
- 调用 `pci_system_init()` 验证 HarmonyOS PCI 后端（sysfs）；
- 真实设备访问可用时执行清理；
- 沙箱受限时仅接受 `EACCES`、`ENOENT` 或 `ENOSYS`。

本地 W3 执行结果：

```text
libpciaccess HarmonyOS platform test: restricted PCI access accepted (13)
```

鸿蒙特有测试：**1/1 通过**。

## 依赖链验证

- `requirements()` 声明 `zlib/1.3.1`（制品仓已发布），`PkgConfigDeps` 生成 `zlib.pc`，meson 构建链接的是 Conan 管理的 zlib（`conan2/p/zlib*/p/lib/libz.a`），非系统库；
- `common_device_name.c`（gzopen 读压缩 pci.ids）参与编译，静态库消费者的 zlib 符号由 Conan 依赖图传递，无未定义符号。

## 结论

- 上游测试：0/0（上游无注册测试项，命令已实际执行）
- 消费者测试：1/1 通过
- 鸿蒙特有测试：1/1 通过
- conan create（含 test_package）exit 0；W3 本地 CI 模拟通过（`.ci-result.json` exit_code=0）
