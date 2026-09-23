# Test Report — nemu 3.5.0

## 概述
- 软件：nemu 3.5.0
- 目标平台：HarmonyOS PC arm64（ohos-aarch64 profile）
- 构建配置：**NM_WITH_USB=ON、NM_WITH_OVF_SUPPORT=ON**（对齐上游 `.github/workflows/tests.yml` 测试矩阵；D-Bus/remote/network-map 关闭——需 glib/dbus/graphviz 栈，不影响测试断言的 QEMU 命令行）
- 上游官方测试：共 9 个 Python unittest 集成测试（`test/vm_test.py` 8 个、`test/ova_test.py` 1 个），**在本 OHOS PC 设备上全部真实执行，9/9 通过（100%）**。
- 适配测试：test_package 消费者目标编译/链接成功；包产物 `bin/nemu` 在设备上重签名后实际运行，`--version` 正常输出（`nEMU v3.5.0 + OVF import + USB Support`）。

## 上游测试统计
| 项目 | 用例数 | 通过数 | 说明 |
|------|--------|--------|------|
| 上游官方测试程序 | 9 | **9** | `python3 -m unittest -v vm_test ova_test` 于 2026-09-11 在 HarmonyOS PC（HongMeng Kernel 1.12.0 aarch64）设备实测 |
| 上游测试断言 | 9 | **9** | `Ran 9 tests in 7.620s — OK`（原始输出见下） |

### 逐用例实测结果
| 用例 | 说明 | 结果 |
|------|------|------|
| vm_test.TestVm.test_01_install | VM install（TUI 键序建 VM → 比对生成的 QEMU 命令行） | ok |
| vm_test.TestVm.test_02_edit_base_settings | Edit main settings（改内存/CPU/磁盘接口/双网卡） | ok |
| vm_test.TestVm.test_03_clone | Clone VM | ok |
| vm_test.TestVm.test_04_edit_viewer_settings | Edit viewer settings（串口/VNC/USB tablet） | ok |
| vm_test.TestVm.test_05_share_9pfs | Share host filesystem（9p 共享） | ok |
| vm_test.TestVm.test_06_additional_drive | Add/Delete additional drive（SCSI 二盘 + 删除） | ok |
| vm_test.TestVm.test_07_boot_settings | Edit boot settings（BIOS/pflash/kernel/initrd/gdb） | ok |
| vm_test.TestVm.test_08_network | Network settings（vmxnet3/user 网络端口转发） | ok |
| ova_test.TestOVA.test_01_install | OVA import（OVA 解包 → OVF 解析 → 磁盘转换入册） | ok |

### 原始输出（实测留档）
```text
test_01_install (vm_test.TestVm.test_01_install)
* VM install ... ok
test_02_edit_base_settings (vm_test.TestVm.test_02_edit_base_settings)
* Edit main settings ... ok
test_03_clone (vm_test.TestVm.test_03_clone)
* Clone VM ... ok
test_04_edit_viewer_settings (vm_test.TestVm.test_04_edit_viewer_settings)
* Edit viewer settings ... ok
test_05_share_9pfs (vm_test.TestVm.test_05_share_9pfs)
* Share host filesystem ... ok
test_06_additional_drive (vm_test.TestVm.test_06_additional_drive)
* Add/Delete additional drive ... ok
test_07_boot_settings (vm_test.TestVm.test_07_boot_settings)
* Edit boot settings ... ok
test_08_network (vm_test.TestVm.test_08_network)
* Network settings ... ok
test_01_install (ova_test.TestOVA.test_01_install)
* OVA import ... ok

----------------------------------------------------------------------
Ran 9 tests in 7.620s

OK
== upstream tests exit: 0 ==
```

复现入口：`bash archives/n/nemu/3.5.0/test_files/run-upstream-tests.sh <pkg-dir> <src-dir>`（一键：沙箱布置 → 环境适配层编译 → 9 用例执行）。

## 真跑环境的技术适配（不改上游任何文件）
上游测试为「tmux 驱动 TUI 键序 + 比对 nemu 生成的 QEMU 命令行」的集成测试，对宿主环境有 5 项前置。本 OHOS 设备的真实差异与适配层（`test_files/`，全部经环境变量/注入实现，**上游源码与测试文件零修改**）：

| # | 上游前置 | OHOS 实况 | 适配（test_files） |
|---|----------|-----------|--------------------|
| 1 | 可写 `/tmp`（测试硬编码 `/tmp/nemu_<uuid>`，不读 TMPDIR） | 根 `/tmp` 为只读 erofs，无 CAP_SYS_ADMIN 无法重挂 | 双层重定向到可写 tmpfs：C 层 `LD_PRELOAD`（nemu 二进制，open/openat/stat/fopen/mkdir/mkdtemp/chdir/statvfs/execvp…）+ python 层 `sitecustomize.py`（python.org 构建的 libpython 为 BIND_NOW，其 os.mkdir 不经可拦截的 PLT 解析路径——实测拦截不到，故 python 侧包一层：os.mkdir/stat/open、builtins.open、os.PathLike、shutil、subprocess） |
| 2 | `getpwuid()` 返回 home（nEMU 启动必需） | OHOS 无 `/etc/passwd`，getpwuid 返回 NULL → `Error get home directory` 退出 255 | preload 提供 `getpwuid` 伪结构（home 指向沙箱） |
| 3 | `qemu-system-x86_64 -M help`、`qemu-img create/convert`（nemu 探测机型/建盘） | 设备无 QEMU | `qemu-system-x86_64.stub`（`-M help` 机型表含 `(default)` 标记，`pc` 为默认机型）+ `qemu-img.stub`（create/convert 语义）。**测试断言的是 nemu 生成的 QEMU 命令行字符串，不实际启动 QEMU** |
| 4 | `tmux`（TUI 宿主） | 设备无 tmux | 按仓内 `archives/t/tmux/3.4` 配方编译静态 tmux 3.4（libevent 2.1.12 + ncurses conan 包 + 6 补丁）；socket 目录用 tmpfs（HMDFS 上 unix socket bind 被拒） |
| 5 | ELF 代码签名（设备执行 conan 产物） | Conan 产物签名未被本机校验接受 → execve EPERM | `binary-sign-tool -selfSign 1` 重签名（沙箱副本，不改包产物本身） |

另两处实测平台差异（已在适配层内消化）：
- **tmux 会话子进程无法读取 HMDFS 文件**（open() EACCES，与直接子进程行为不同）——测试源码与 OVA 数据复制到 tmpfs 沙箱后再跑。
- **OVA 测试数据**：上游 `run.sh` 依赖 `gdown` 从 Google Drive 拉 `dsl.ova`（本环境外网不可达）。按 OVF 1.0 envelope（`test_files/dsl.ovf`）构造功能等价的 `dsl.ova`——nemu 的 OVA import 断言只依赖 envelope 元数据（name=DSL、256MB 内存、1 vCPU、1 网卡、disk fileRef→`Damn_Small_Linux-disk1.vmdk`）与文件名，磁盘内容不作要求（qemu-img convert 由桩执行）。OVA 为未压缩 tar（nemu 只启用 `archive_read_support_format_tar`，与上游 dsl.ova 一致）。

## 适配后测试统计
| 测试边界 | 结果 | 说明 |
|----------|------|------|
| Conan G2 | PASS | `conan create` 干净重建成功（USB/OVF 开启，链接 libxml2/libarchive/libusb/libudev 链） |
| test_package 编译/链接 | PASS | `test_nemu` 编译链接成功 |
| test_package 运行 | PASS | 本设备重签名后实际运行 `nemu --version` 正常输出（`nEMU v3.5.0` + 特性矩阵） |
| 上游测试 | **PASS 9/9（100%）** | 本设备真跑，`Ran 9 tests — OK` |

## 断言统计
- 上游测试断言：**9/9（100%）**
- 适配测试运行断言：`nemu --version` 实际执行成功（OHOS 设备本机）
- 上游测试覆盖的适配面（真跑即验证）：CMake 构建矩阵（USB/OVF）、SQLite VM 库表、TUI 表单全流程（install/edit/clone/viewer/9p/drive/boot/network）、OVA 解包与 OVF XPath 解析、QEMU 命令行生成（含 `-enable-kvm -cpu host`、机型 `pc`、网络/磁盘/串口/9p 参数拼接）。

## 门禁结果
- G0：PASS
- G1：PASS
- G2：PASS（干净重建）
- G3：PASS
- G4：PASS（bin/nemu、bin/ntty、share/ 模板与 locale 产物齐全）
- L2：PASS（设备本机 `--version` 实跑）
- L4：PASS
- L5：PASS

## 产物
- `bin/nemu`（NEEDED: libjson-c.so.5 / libintl.so.8 / libxml2.so.16 / libarchive.so.13 / libusb-1.0.so.0）
- `bin/ntty`（shell 脚本）
- `share/nemu/templates/config/nemu.cfg.sample`
- `share/locale/ru/LC_MESSAGES/nemu.mo`

## 说明
- QEMU 本体（qemu-system-x86_64/qemu-img）在 OHOS PC 上不可用（上游亦未打包），测试桩只服务于命令行生成路径的验证；**虚拟机的实际启动属 QEMU 生态范围**，nemu 作为 TUI 管理器的全部管理流（建/改/克隆/网络/OVA 导入）已被 9 用例真实覆盖。
- `qemu_bin_path` 等运行时路径由 `nemu.cfg` 配置（`share/nemu/templates/config/nemu.cfg.sample` 提供），部署侧可指向任意 QEMU 发行版。
