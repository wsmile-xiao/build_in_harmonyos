# kernel-headers 6.12.77 测试报告

- 日期：2026-09-18
- 环境：OpenHarmony PC（aarch64），clang 15.0.4（OHOS SDK），libc++，C17/C++17
- conan profile：ci/conan/profiles/ohos-aarch64（os=OHOS/arch=armv8/clang15/libc++/cppstd=17/Release）
- 验证命令：`conan create . -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing`

## 一、上游测试（rule4 N 申报口径）

### N 核验：以实际构建系统注册为准

Linux kernel 6.12 构建系统（kbuild）**无测试套件注册**：

- 顶层 Makefile grep `headers_check` 无目标（该验证目标已随 5.x kbuild
  演进从 Makefile 移除），仅存 `headers_install`/`headers` 导出目标；
- 无 add_test/ctest/Makefile test 规则等价物；
- 导出管线自带校验（scripts/headers_install.sh 逐头 sed 清洗 +
  Kbuild no-export-headers 排除）随 `make headers` 一体执行，
  属构建步骤而非注册测试目标。

### 申报数字（如实申报）

| 口径 | 数量 |
|---|---|
| 上游构建系统注册测试目标 N | **0**（kbuild 无测试注册，headers_check 已移除） |
| 导出头文件数（HDRINST 产物） | 963 |
| 导出管线内建校验（随构建执行） | headers_install.sh 逐头清洗，全部通过（无输出即无失败） |

### 上游测试缺失原因（正文如实申报）

纯头文件包：上游交付物即头文件树本身，Linux 内核的回归测试体系
（kselftest/KUnit）是内核镜像运行期测试，与 UAPI 头文件包消费者无关
（不需要内核运行环境）；UAPI 头的正确性验证由消费者编译验证承担。

## 二、test_package（消费者视角，R34）

### 测试内容

test_kernel_headers.c：单一翻译单元联合编译 9 个代表性 UAPI 头：

- `linux/version.h`：编译期 `#error` 断言 `LINUX_VERSION_CODE ==
  KERNEL_VERSION(6,12,77)` + `LINUX_VERSION_MAJOR/PATCHLEVEL/SUBLEVEL`
  宏存在性断言（编译期 2 项）
- `linux/types.h`（__u16/__u32）、`linux/input.h`（struct input_id/
  BUS_USB）、`linux/input-event-codes.h`（KEY_A）、`linux/if_ether.h`
  （ETH_P_IP）、`linux/ioctl.h`（_IOC 宏）、`asm/byteorder.h`、
  `asm/posix_types.h`、`asm/unistd.h`（arm64 syscall 表编号断言：
  `__NR_io_setup == 0 && __NR_openat == 56`）——运行期联合断言
  （6 项 + 版本三元组 3 项）

### 执行结果

```
conan create … → test_package:
[ 50%] Building C object CMakeFiles/test_kernel_headers.dir/test_kernel_headers.c.obj
[100%] Linking C executable test_kernel_headers
kernel-headers/6.12.77 (test package): RUN: ./test_kernel_headers
→ 退出码 0（PASS，1/1 通过）
```

| 口径 | 数量 |
|---|---|
| test_package 用例 | 1（test_kernel_headers.c） |
| 编译期断言 | 2（#error 版本一致性 + 宏存在性） |
| 运行期断言 | 8 |
| 通过 | 1/1（100%） |

## 三、包产物完整性（G4）

- include/ 下 963 个 UAPI 头文件（linux/ asm/ asm-generic/ drm/ misc/
  mtd/ rdma/ regulator/ scsi/ sound/ video/ xen/）
- `include/linux/version.h`：LINUX_VERSION_CODE=396365（6.12.77）✓
- asm/ 38 头均为 arm64 语义（wrapper + unistd_64.h）✓
- licenses/（GPL-2.0 + Linux-syscall-note）✓

## 四、L4/L5 门禁

- 纯头文件包无二进制产物（bindirs/libdirs 置空）→ L4 smoke
  （--version）不适用、L5 安全扫描（NX/PIE/RELRO）不适用——由
  test_package 可执行文件编译链接运行代替验证

## 五、结论

- 上游注册测试 N=0（如实申报 + 原因）
- 消费者验证 1/1 通过（编译期断言 2 + 运行期断言 8 全部成立）
- 包产物 963 头文件完整，版本宏正确
- **适配验证通过，状态 built**
