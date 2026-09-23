## PR 信息
- **三方库名称**：nemu
- **上游版本**：3.5.0（tag v3.5.0）
- **上游仓库地址**：https://github.com/nemuTUI/nemu
  - 源码包：https://github.com/nemuTUI/nemu/archive/refs/tags/v3.5.0.tar.gz（官方 tag 源，sha256 见 conandata.yml）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent skill；同仓配方 tmux/3.4（测试宿主）、leptonica 1.85.0（/tmp 只读 LD_PRELOAD 重定向范式、CONFIG 注入 IMPORTED target 范式）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 集成测试 | 9 | `test/vm_test.py` 8 个 `test_*`（install/edit_base/edit_viewer/clone/9pfs/drive/boot/network）+ `test/ova_test.py` 1 个（OVA import）；由 `test/run.sh` 以 `python3 -m unittest -v *_test.py` 执行（tmux 驱动 TUI 键序 → 比对 nemu 生成的 QEMU 命令行） |
| 其他测试 | 0 | `test/run.sh` 仅负责下载 OVA 测试数据并启动上述 9 个 unittest 用例 |
| **合计** | **9** | 上游实际测试用例总数为 9 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 通过数 | 说明 |
|----------|-------------|--------|------|
| 上游集成测试 | 9 | **9** | 在 HarmonyOS PC 设备（HongMeng Kernel 1.12.0 aarch64）真实执行 `python3 -m unittest -v vm_test ova_test`，`Ran 9 tests in 7.620s — OK`（逐用例结果见 reports/test-report.md） |
| test_package | 1 | 1 | 消费者目标编译链接通过；`nemu --version` 在本机重签名后实际运行正常输出（`nEMU v3.5.0 + OVF import + USB Support`） |
| **合计** | **10** | **10（100%）** | |

## 上游测试用例修改说明

无修改。上游测试文件（`test/vm_test.py`、`test/ova_test.py`、`test/utils.py`、`test/run.sh`、`test/tmux.conf`、`test/nemu.cfg.in`）保持原样。

上游测试的 5 项宿主前置在 OHOS PC 上的差异，全部由 `test_files/` 环境适配层解决（环境注入，不改上游源码与测试）：

| 上游前置 | OHOS 实况 | 适配（test_files/） |
|----------|-----------|---------------------|
| 可写 `/tmp`（测试硬编码，不读 TMPDIR） | 只读 erofs，无 CAP_SYS_ADMIN | 双层重定向到可写 tmpfs：C 层 `LD_PRELOAD`（nemu 二进制）+ python 层 `sitecustomize.py`（python.org 构建的 libpython 为 BIND_NOW，LD_PRELOAD 拦不到其 os.mkdir——实测定位，故 python 侧单独包装） |
| `getpwuid()` 返回 home | 无 /etc/passwd，getpwuid NULL → 启动即退 | preload 提供伪 passwd 结构 |
| `qemu-system-x86_64 -M help` / `qemu-img` | 设备无 QEMU | 测试桩（`-M help` 机型表 + create/convert 语义）。**测试断言对象是 nemu 生成的 QEMU 命令行字符串，非实际启动 VM** |
| `tmux` | 设备无 tmux | 按仓内 `archives/t/tmux/3.4` 配方构建静态 tmux 3.4；socket 目录用 tmpfs（HMDFS 上 unix socket bind 被拒——实测） |
| ELF 代码签名 | Conan 产物签名未被本机接受 → execve EPERM | `binary-sign-tool -selfSign 1` 重签名沙箱副本 |

实测发现的平台差异（已在适配层消化，上游零修改）：
- tmux daemonize 后的 pane 子进程 open HMDFS 文件返回 EACCES（直接子进程正常）→ 测试源码与数据 tmpfs 化
- OVA 测试数据（上游 `run.sh` 依赖 `gdown` 从 Google Drive 拉 `dsl.ova`，外网不可达）→ 按 OVF 1.0 envelope 构造功能等价 `dsl.ova`（nemu 的 OVA import 断言只依赖 envelope 元数据与文件名，磁盘内容不作要求；OVA 为未压缩 tar，与上游一致——nemu 只启用 tar 格式支持）

一键复现：`bash archives/n/nemu/3.5.0/test_files/run-upstream-tests.sh <pkg-dir> <src-dir>`

## 补全测试用例说明

- 新增 `test_files/`（上游测试环境适配层，非新测试）：`nemu_test_env.c`（LD_PRELOAD）、`sitecustomize.py`（python 层）、`qemu-system-x86_64.stub`/`qemu-img.stub`（QEMU 桩）、`dsl.ovf`（OVA 数据模板）、`run-upstream-tests.sh`（一键入口）
- test_package（前人已有，保留）：fork/exec 方式调用 `nemu --version` 并传播退出状态

## 验证结果

- **编译状态**：✅ 通过（`conan create` 干净重建成功；构建矩阵对齐上游 `.github/workflows/tests.yml`：`NM_WITH_USB=ON`、`NM_WITH_OVF_SUPPORT=ON`）
- **测试通过率**：✅ 上游 9/9 = **100%**（设备真跑，`Ran 9 tests — OK`）；test_package 1/1（编译链接 + 本机重签名实跑）
- W3 本地 CI：Build Summary 100%（1/1），L1a/L1b/L1e（破坏性反向验证）全过
- 门禁：G0-G4 / L2 / L4 / L5 全 PASS

### 构建配置说明
- D-Bus / remote control / network map 关闭（需 glib/dbus/graphviz 栈，超出适配范围；不影响测试断言的 QEMU 命令行——上游 tests.yml 开这些开关是为代码覆盖）
- 新增依赖：libusb/1.0.27 + libudev-zero/1.0.4（NM_WITH_USB=ON 所需，制品仓均已发布）
- 补丁 0001 扩展：MODULE→CONFIG 变量桥接（上游用 `${SQLITE3_LIBRARIES}` 等 MODULE 大写变量，CMakeDeps CONFIG 声明不填充）+ `Intl::Intl` 空 target 的 libintl 注入（gettext 包未声明 cpp_info.libs）

## 补充说明

- **分支重建声明**：本分支基于最新 main（8f05a4eb33）重建并 force push，替代前人旧分支（原 head 16980dade4，基点为 9 月 4 日 main，相对最新 main diff 5500+ 文件——CI 下载超时的经典模式）。前人归档资产（conanfile/补丁/test_package/manifest）已评估复用；本 PR 在其基础上开启 USB/OVF 构建矩阵并完成上游测试 9/9 真跑。
- QEMU 本体在 OHOS PC 不可用（上游亦未打包）；nemu 作为 TUI 管理器的全部管理流（建/改/克隆/网络/OVA 导入/QEMU 命令行生成）已被 9 用例真实覆盖，VM 实际启动属 QEMU 生态范围（`qemu_bin_path` 由 nemu.cfg 配置，可指向任意 QEMU 发行版）
- 关联平台任务：#6746

---

关联任务：平台任务 #6746（nemu 3.5.0 适配）
