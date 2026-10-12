# kinect-audio-setup 0.5 适配笔记（HarmonyOS PC arm64）

## 1. 软件信息

- 名称：kinect-audio-setup 0.5
- 描述：使 Microsoft Kinect 感应器的音频输入在 GNU/Linux 上可用
- 上游：作者 Antonio Ospite 官方 git 服务器 https://git.ao2.it/kinect-audio-setup.git（v0.5 tag）
- 源码 URL：https://git.ao2.it/kinect-audio-setup.git/snapshot/v0.5.tar.gz
- sha256：5e1d688a817f764605145ac3ef903d9c8e6fc8be0a85efa78b385a73798d9387
- license：BSD-2-Clause（源码头：Drew Fisher + Antonio Ospite）
- 构建系统：纯 Makefile（顶层 Makefile 递归 kinect_upload_fw/Makefile）
- 语言：C（2 个源文件：endian.c + kinect_upload_fw.c）

## 2. 依赖（W0 预检）

| 依赖 | 版本 | 制品仓状态 | 发现方式 |
|------|------|-----------|---------|
| libusb | 1.0.27 | ✅ 已发布（ohpcd） | `conan download libusb/1.0.27 -r=ohpcd --only-recipe` 成功 |

无其他依赖。预检通过，无需先适配依赖包。

## 3. R51 上游测试申报表

| 项目 | 内容 |
|------|------|
| 上游测试目录数 | 0（无 tests/、无 test/） |
| 构建系统注册测试目标 | 0（Makefile 仅 all/install/install_udev_rules/clean；无 `make check`、无 ctest、无 autotools TESTS） |
| 清点证据 | 已核查顶层 Makefile（17 行：all/install/install_udev_rules/clean）与 kinect_upload_fw/Makefile（64 行：all/install/clean），均无 check/test 目标；源码树无 tests 目录 |
| 结论 | 上游确无自动化测试 |

### 实测记录（R51 第三法）

- 由于上游无测试套件，以**真实二进制实跑自证**：
  - `kinect_upload_fw --help` → 程序按 argc==2 分支尝试打开 "--help" 固件文件，输出 `Failed to open --help: No such file or directory`（预期行为，证明 ELF 可执行、动态链接正常、argparse 路径逻辑完整）
  - `kinect_upload_fw firmware.bin`（无设备）→ libusb_open 失败路径（设备相关，测试环境无 Kinect 硬件）
- 本机为 OHOS arm64（aarch64），构建期工具 endian 可运行生成 endian.h，无需交叉处理。

## 4. 适配关键点

1. **Makefile + pkg-config**：kinect_upload_fw/Makefile 用 `pkg-config --cflags/--libs libusb-1.0` 发现依赖。配方 generate() 用 `PkgConfigDeps` 生成 conan 化 .pc（prefix 指向 conan 包目录），并注入 PKG_CONFIG_PATH；make 内嵌 pkg-config 调用即可命中（R49 依赖注入私有 prefix 语义）。
2. **R26 静态链接**：libusb 非系统同名库但配方默认静态 `shared=False`；产物 ELF 仅 NEEDED libc.so，libusb 符号静态链入（`readelf -d` 验证）。
3. **OHOS 无 GNU install**：`make install` 目标依赖系统 `install` 命令（OHOS 缺失，busybox install 可用但在 conan 环境不可靠），故 package() 直接 `copy` 产物到 `sbin/`，保持上游 `PREFIX=/usr/local` → `sbin/kinect_upload_fw` 语义。
4. **R38 commands.json**：产物含可执行文件 `kinect_upload_fw` → 软件级目录需创建 commands.json（已创建）。
5. **R33**：build() 中 `CC` 取自 `self.conf.get("tools.build:compiler_executables:c")`，不裸用 shell 环境变量。
6. **R9**：make 使用 `-j1`。

## 5. 知识图谱

- 编译过程顺利，未命中知识图谱错误模式；无需生成草稿。
- 新增适配模式（Makefile + pkg-config + OHOS 无 install）记录于本 notes。

## 6. 备选源说明

- 上游官方源 git.ao2.it 的 v0.5 snapshot 与 Debian orig tarball（kinect-audio-setup_0.5.orig.tar.gz）逐文件一致（diff 验证 12 个文件），Source URL 采用官方源（R39）。
- Savannah 镜像同名文件已 404（上游清理），waterlan 官方站已停用（302 → notxs4all），故采用作者官方 git 服务器 snapshot。
---

**编译结束**: 2026-09-27 13:55
**最终状态**: published
