# umtprd 1.6.8 notes

## Scope

uMTP-Responder（viveris/uMTP-Responder tag umtprd-1.6.8）：轻量纯 C 实现的
USB MTP responder 守护进程，对接 Linux FunctionFS/libcomposite 或 GadgetFS，
通过设备 USB 口提供文件传输。本配方交付 `bin/umtprd` 守护进程二进制 +
`res/umtprd.conf` 示例配置，在 HarmonyOS PC（aarch64）原生构建。

任务分支：feat/umtprd-1.6.8。

## Upstream shape (umtprd-1.6.8 tag, 2024-07-08)

- 手写 Makefile 工程（目标仅 all/clean/help）：无 configure、无 check/test
  目标、无 install 目标；`make CC=<cross-gcc>` 即完成构建，产物为根目录
  `./umtprd` 单二进制。
- 源码布局：src/*.c（含 mtp_operations/ 子目录约 30 个 MTP 操作实现）、
  inc/*.h、conf/umtprd.conf 示例配置、README.md。
- 可选构建开关（默认全关，本配方保持默认）：USE_SYSLOG=1（syslog 支持）、
  SYSTEMD=1（需 libsystemd，OHOS 无此库，不开）、DEBUG=1（调试输出）、
  OLD_FUNCTIONFS_DESCRIPTORS=1（<3.15 老内核，不开）。
- 无测试：无 tests/ 或 test/ 目录；Makefile 无 check/TESTS 目标；
  无 ctest/pyest/gtest 绑定（N=0，审计见 test_package/MANIFEST.yml）。

## Adaptations

构建时 OHOS 适配（无 patches/ 文件，conanfile build() 内完成，
ext4fuse 0.1.3 先例）：

1. E085 pthread_cancel（2026-10-12 真机 compile 失败，未提交）：
   OHOS musl 以 `musl_use_pthread_cancel=false` 构建，不提供
   `pthread_cancel` 符号，链接期报
   `ld.lld: error: undefined symbol: pthread_cancel`
  （src/usb_gadget.c 两处：handle_ep0 的 GADGETFS_DISCONNECT 处理、
   deinit_usb_mtp_gadget）。两处调用前均已置 `stop=1`，且 io_thread()
   轮询该标志退出，因此 `__OHOS__` 下仅 `pthread_join` 即可回收线程
   （bwfmetaedit 26.01 / dvgrab 3.8 / axel 2.17.14 先例）。
   实现为精确语句级改写（不断言行号，每处 `count==1` 断言，marker 保证
   幂等；Linux 下为 no-op，上游行为不变）。其余 pthread 系列
   （create/join/mutex/kill）OHOS musl 均提供，无需处理。

源码仅依赖 libc（pthread/inotify/System V msgqueue）与 Linux USB
gadget 头文件（linux/usb/ch9.h、linux/usb/gadgetfs.h），均由 OHOS
sysroot 提供；R8/PF5：除上述 E085 能力缺失外无实质逻辑需求，不造补丁。

构建命令（conanfile.py build()）：`make -j1 CC=<conan conf c 编译器>`，
R33 合规（编译器取自 tools.build:compiler_executables:c，不用裸 ${CC}）；
make 取 user.hmbs:make_path / HMBS_MAKE，回退 plain make；全程 -j1（R9）。

安装：上游无 install 目标，package() 手工拷贝：
bin/umtprd、res/umtprd.conf（conf/umtprd.conf）、licenses/LICENSE。

## Verification

- 上游测试：N=0（上游无任何测试框架；见 test_package/MANIFEST.yml 审计）。
- 消费者测试（test_package，5 断言，test_umtprd.sh）：
  1. `bin/umtprd` 存在且带可执行位；
  2. 无参运行输出非空（15 秒 timeout 兜底；默认 loop_on_disconnect=0，
     单次 USB 初始化失败即退出，不会常驻）；
  3. 输出含 `uMTP Responder` banner（ELF 加载 + libc printf 路径）；
  4. 输出含 `Version:`（版本字符串正确编入）；
  5. 否定对照：退出码非零（无 /dev/ffs-umtp/ep0 设备节点时走优雅
     USB-init-failure 路径返回 2；exit-0 桩二进制在此用例失败，证明
     harness 能抓到假通过）。
- 真机预检结论以 HMBS 返回的 evidence 为准，本轮尚未验证。

## Notes

- 2026-10-12 真机 compile 失败修复（未提交）：conf 的 `tools.build:compiler_executables:c`
  仍指向 `/data/service/hnp/bin/clang`，但真机上该文件已不存在
  （`make: /data/service/hnp/bin/clang: No such file or directory`，Error 127）。
  build() 改为“conf 优先、存在性校验、PATH 回退”：conf 路径存在才用，
  否则用 `CC env → which clang/cc/gcc` 解析并打印 `HMBS: using CC=` 诊断行；
  仍 R33 合规（首选 conf，不裸用 shell 变量），仅不再向 make 传递不存在的绝对路径。

- R40 边界说明：完整 MTP 服务需要 USB FunctionFS/GadgetFS 设备节点与
  USB device 口直通，HarmonyOS PC 无此硬件路径；本适配以守护进程二进制
  交付 + 用户态路径（banner/配置解析/优雅失败）验证为边界，不虚构
  HAL 适配（usbmuxd 1.0.8 先例：同样声明守护进程直通边界）。
- conandata.yml sha256 取自 Buildroot 上游 umtprd.hash
 （umtprd-1.6.8.tar.gz → e0b3c308…ff3574），URL 为官方 GitHub tag 归档
  （R39 官方源口径；CI 自动加镜像 fallback）。
- 零 conan 依赖（W0/R36 无阻塞）：pthread 等均由 OHOS libc/sysroot 提供。
- commands.json type=tool（usbmuxd/kfourinline 先例：守护进程/工具型交付
  必须 "tool"，type=app 会被 L0k 拦截）。
