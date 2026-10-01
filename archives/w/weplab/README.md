# weplab 0.1.5

WEP protocol teaching and key-cracking tool.

## 适配状态

- 版本：0.1.5
- 构建系统：autotools
- 依赖：libpcap/1.10.6
- 产物类型：CLI 工具（单二进制）
- OHOS 适配状态：已适配

## 平台修改

1. `patches/0001-fix-gcc-arch-flags.patch`：移除 configure.ac 中 x86 专属的 gcc 架构优化标志块（`-march=pentium4`、`-msse` 等），避免在 aarch64 clang 上产生无效标志。
2. `patches/0002-fix-config-sub-aarch64-ohos.patch`：修补 tarball 自带（2005 年）的 config.sub，识别 `aarch64-linux-ohos` triplet。
3. `conanfile.py`：`generate()` 用 AutotoolsDeps/Toolchain 生成依赖环境（E430 修复），`build()` 向 configure 显式传 `-I`/`-L`/`-lpcap`；因 automake 1.4 的 make 触发 recheck 在 OHOS 沙箱失败，从生成的 Makefile 提取编译参数逐文件编译后直接链接；`-std=gnu89` 恢复 upstream inline 函数外部符号语义；`-Wl,--allow-multiple-definition` 匹配原始 `-fcommon` 行为。
4. `conanfile.py`（CI 构建修复）：CI 工作机构建缓存位于 HMDFS/FUSE 挂载，config.status 的 `mktemp -d`（硬编码 0700）临时目录不可写导致 Makefile 生成失败；`build()` 在 Makefile 缺失时改写 config.status 的临时目录创建（umask 022 + mkdir，创建时即 0755）并重跑。

## 上游测试

上游无自动化测试套件。`make check` 解析为 `check-am: all-am`，无实际测试目标。

## 鸿蒙测试

test_package 共 17 项用例：15 项通过 + 2 项显式跳过（live capture 需无线网卡与 root、pcap 分析需真实输入文件）。新增鸿蒙消费者用例：`ohos_pcap_format_probe.c`（8 探针，运行时 PASS/FAIL，非断言式）— 逐项覆盖 weplab 真实消费的 libpcap 面：DLT_IEEE802_11/DLT_PRISM_HEADER 常量（capture.c 判别值）、pcap_open_dead + pcap_datalink、savefile 写入路径（pcap_dump_open/dump/flush/close → 56 字节合法文件）、离线读取路径（pcap_open_offline + pcap_next 回读同一包，caplen=16）、离线打开失败分支（NULL + errbuf，wep.c:OpenPcapFile 依赖）与链路层名表边界契约；`pcap_close` 释放仅作清理、因返回 void 无判据而不计入通过数。
