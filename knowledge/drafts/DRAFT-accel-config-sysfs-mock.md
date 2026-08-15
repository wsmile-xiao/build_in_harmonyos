# DRAFT-accel-config-sysfs-mock: Linux 硬件加速器配置库在 OpenHarmony 上的用户态可移植边界与 mock sysfs 安全验证方法

> **Contributor**: AtomCode | **Status**: Draft | **Updated**: 2026-08-13
> **Severity**: 3 | **Category**: autotools / sysfs / driver / portability / testing / idxd

## 错误特征

```text
sh: aclocal: inaccessible or not found
autoreconf: error: aclocal failed with exit status: 127
libtoolize: error: $pkgauxdir is not a directory: '//share/libtool/build-aux'
configure.ac:40: error: possibly undefined macro: AC_DEFINE
configure: error: cannot guess build type
config.status: error: could not setup config files machinery
immintrin.h:14:2: error: "This header is only meant to be used on x86 and x64 architecture"
'uuid/uuid.h' file not found
idxd kernel module not loaded
Error relocating ...: json_object_new_array: symbol not found
```

## 触发条件

- 软件: accel-config（上游 intel/idxd-config，tag accel-config-v4.1.9）
- 语言/构建: C / Autotools（configure.ac + Makefile.am + autogen.sh）
- 平台: OpenHarmony PC (arm64)，真机无 Intel DSA/IAA 硬件、无 /sys/bus/dsa、无 /dev/dsa
- 阶段: configuration / compilation / testing / runtime

## 根因分析

accel-config 由用户态库 libaccel-config 与 CLI accel-config 组成，可分三层看待：

1. **可移植层（纯用户态）**：config.c / config_attr.c 的 JSON 配置解析（json-c）、
   util/ 下 strbuf/bitmap/size/filter/parse-options 等工具、accfg_new/accfg_get_log_priority
   等不触碰 sysfs 的 API。这些可在 OHOS arm64 编译并运行。
2. **Linux 专有层（可编译不可验证）**：设备枚举（`/sys/bus/%s/devices`）、属性读写
   （sysfs_read_attr/write_attr）、bind/unbind（`/sys/bus/dsa/drivers/idxd/bind`）、
   `/sys/module/idxd` 存在性检查、`/dev/%s/wqX.Y` 字符设备路径构造、IDXD_SCMD_* ioctl
   状态码（accfg/idxd.h）。全部硬编码 /sys 与 /dev，强依赖 idxd 内核驱动与 Intel 硬件。
3. **不可移植层（硬件测试）**：test/ 的 dsa_test.c / iaa_test.c / libaccfg.c 直接 include
   x86 专有头（immintrin.h/mmintrin.h 等），arm64 交叉编译直接失败；runner 脚本
   （dsa_user_test_runner.sh / dsa_config_test_runner.sh / iaa_user_test_runner.sh）与
   test_all.sh 全部需要真实 DSA/IAA 设备、pasid_enabled=1、kernel >= 5.6，且
   dsa_config_test_runner 会写真实设备配置，禁止在无硬件环境运行。

编译链路首错链：构建机缺 automake/aclocal（127）→ autom4te 在只读 /tmp 建临时文件失败
（用 $TMPDIR）→ config.guess 不认识 HarmonyOS（cannot guess build type，E007 同族）→
config.status 的 mktemp 相对模板在受限 FS 上 Permission denied → PKG_CHECK_MODULES
的 pkg.m4 未被 aclocal 收录导致误导性 "possibly undefined macro: AC_DEFINE" → 依赖
.pc 文件 include 前缀错误导致 uuid/uuid.h 找不到。

## 解决方案

### 推荐方案（sysfs-root-injection-and-layer-aware-testing）

1. **构建期工具闭环**：从 ohpcd Conan remote 获取 automake/1.18 + libtool/2.5.4，
   部署到 $HOME/autotools（不写系统目录），固定 PATH / ACLOCAL_PATH（libtool 的
   share/aclocal 与 pkg-config 的 share/aclocal 都要加）/ _lt_pkgdatadir
   （指向 libtool-conan 包目录）。
2. **环境修复**：TMPDIR 指向 $HOME 可写目录；config.guess/config.sub 打 HarmonyOS 补丁
   （复用 util-linux 2.39 0001/0002 补丁模式，输出 aarch64-unknown-linux-ohos）；
   config.status 的 mktemp 改 ${TMPDIR:-/tmp}/conf$$-$RANDOM + mkdir -p。
3. **依赖闭环**：json-c/0.17 与 uuid/2.40.1（util-linux 的 libuuid 拆分，包名 uuid 不是
   libuuid）均在 ohpcd 有 recipe 与 main 归档；用 conan install 获取后自建 .pc 指向
   包真实 include/lib 路径（注意 uuid 的 Cflags 是 -I${includedir} 而不是 .../uuid）。
4. **正式配置**：--host=aarch64-unknown-linux-gnu --disable-docs --disable-test
   --with-bash-completion-dir=no；make -j1；make install。
5. **sysfs root 注入补丁**：libaccfg.c 增加 sysfs_root()/sysfs_driver_bind_path()，
   accel-config.c 增加 accfg_sysfs_module_path()，统一读 ACCFG_SYSFS_ROOT 环境变量
   （未设置时保持 "/sys"，不改变生产语义）；替换 4 处硬编码路径。
6. **测试分层（不混写）**：
   - A 层：上游 4 个 TESTS 入口 + 16 个 test_all.sh 用例 + libaccfg/dsa/iaa 程序，
     全部如实记录 hardware-unrunnable（上游 EXIT_SKIP=77 的真实条件：kernel<5.6、
     pasid_enabled!=1、无设备），不删除断言、不伪造 passed。
   - B 层：test_package 用 pkg-config 消费 libaccel-config，编译链接消费者程序，
     调用只读 API（accfg_new / accfg_get_log_priority / accfg_set_log_priority /
     accfg_unref），accel-config --help/--version，真实 self.run()。
   - C 层：ACCFG_SYSFS_ROOT 指向仓库外临时 mock sysfs 树（bus/dsa/devices/dsa0 及
     wq/engine/group 子目录与属性文件），只验证只读枚举、属性解析、JSON 配置解析、
     空设备树返回 []、无 module 报 "idxd kernel module not loaded" 错误路径。
   - 严禁模拟 bind/unbind 成功或真实 DMA。

### 回退方案

若 mock sysfs 需要大量侵入性重构，不强行实现；退化为纯逻辑单元测试（JSON/属性解析）
+ 明确硬件边界，禁止删除断言或伪造通过。

## 验证

```bash
# 最小交叉编译（仓库外探针，真实执行结果）
./autogen.sh                  # exit=0（修复后）
./configure --host=aarch64-unknown-linux-gnu --disable-docs --disable-test \
  --with-bash-completion-dir=no  # exit=0（修复 config.guess/config.status 后）
make -j1                      # exit=0
make install                  # exit=0
# 产物：libaccel-config.so.1.0.0 (ELF arm64, SONAME libaccel-config.so.1,
#       352 导出符号, NEEDED libc.so)、accel-config CLI (NEEDED libaccel-config.so.1/
#       libjson-c.so.5/libc.so)、libaccel-config.pc (Version 4.1.9)、
#       include/accel-config/libaccel_config.h
# 消费者：pkg-config 消费 + 编译链接 + 只读 API → "consumer PASS"
# mock：ACCFG_SYSFS_ROOT=<mock> accel-config list → 枚举 dsa0；
#       空树 → []；无 module → "idxd kernel module not loaded"
```

## 查重差异

已有泛化条目：E002（/tmp 只读）、E007（config.guess/HarmonyOS）、E046（chmod/SELinux）、
E051（未实现 syscall）、E258（meson.options 双文件）。均未覆盖「Linux 硬件加速器配置库
（sysfs/idxd 驱动/DSA/IAA）的用户态可移植边界」与「ACCFG_SYSFS_ROOT mock sysfs 无设备
安全验证方法」这一组合主题；knowledge/ 全库无 accel-config/idxd-config/Intel DSA/IAA
相关条目（13 个关键词扫描仅 arm64 泛化命中 3 个无关文件）。

## 适用范围与安全边界

- 适用：accel-config 4.1.9 及其后续版本、其他依赖 sysfs/字符设备/内核驱动的
  Linux 硬件管理库（Autotools 构建）的可移植边界评估与无设备安全测试。
- 不适用：需要真实 DSA/IAA 性能/功能验证的场景（只能上真机）。
- 安全边界：不写真实 /sys 与 /dev 设备节点、不加载/卸载 idxd 模块、不绑定/启用/
  禁用/配置真实设备与 work queue、不运行会改设备配置的测试、不伪造硬件与 skip、
  把缺硬件写成 passed 是违规行为。

## 清理方法

- 探针目录 $HOME/accel-probe-4.1.9/ 为仓库外临时目录，可直接删除；
- $HOME/autotools/ 为构建期工具部署目录，不进入 PR；
- mock sysfs 树为仓库外临时文件，删除即清理；
- 仓库内仅保留归档文件与知识草稿，无构建残留。
