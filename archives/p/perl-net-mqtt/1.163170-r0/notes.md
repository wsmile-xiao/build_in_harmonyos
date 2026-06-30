# perl-net-mqtt 1.163170-r0 适配笔记

## 编译环境
- 构建系统: custom (perl Makefile.PL + make + make install)
- 编译日期: 2026-06-29
- 编译器: clang/clang++ (纯 Perl 模块，无 C/C++ 编译)
- 状态: published

## 编译步骤

1. `perl Makefile.PL` — 生成 Makefile
2. `make` — 编译纯 Perl 模块到 blib/
3. `make install DESTDIR=$PACKAGE_FOLDER` — 安装到 Conan 包目录
4. package() 方法将 .pm/.pod 文件从 Perl 安装路径复制到 `lib/`，将脚本复制到 `bin/`

关键命令：
```bash
perl Makefile.PL
make
make install DESTDIR=$PACKAGE_FOLDER
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G4 失败：产物为空 | 旧版 conanfile.py 的 package() 路径匹配失败，旧缓存未清除 | 清除 conan 缓存后重新 conan create，package() 正确复制 .pm 到 lib/ |
| 2 | conan-verify L2 失败：脚本无法运行 | bin/ 中的 Perl 脚本找不到 lib/ 中的 Net::MQTT 模块 | 添加 FindBin 补丁：`use FindBin; use lib "$FindBin::Bin/../lib";` |
| 3 | conan-verify L2 失败：--help 返回非零 | `pod2usage(1)` 退出码为 1，L2 期望 0 | 修改为 `pod2usage(-exitstatus => 0, -verbose => 1)` |
| 4 | net-mqtt-trace 无法加载 | 依赖 Net::Pcap 模块未安装 | 改为条件加载：`eval { require Net::Pcap; Net::Pcap->import(); };` |

## 源码修改

### patches/0001-add-findbin.patch

对三个脚本文件 (bin/net-mqtt-pub, bin/net-mqtt-sub, bin/net-mqtt-trace) 的修改：

1. **添加 FindBin 模块定位**：在 `use strict;` 之后添加 `use FindBin; use lib "$FindBin::Bin/../lib";`，使脚本能从 Conan 包的 `bin/` 目录自动定位 `lib/` 中的 Perl 模块
2. **修复 --help 退出码**：将 `pod2usage(1)` 改为 `pod2usage(-exitstatus => 0, -verbose => 1)`，使 --help 返回退出码 0（符合 Unix 惯例和 conan-verify L2 要求）
3. **net-mqtt-trace 条件加载 Net::Pcap**：将 `use Net::Pcap;` 改为 `eval { require Net::Pcap; Net::Pcap->import(); };`，使脚本在缺少 Net::Pcap 时仍可执行 --help

## 依赖版本

- Perl: 5.42.0 (aarch64-linux, /data/service/hnp/perl.org/perl_5.42.0/)
- Conan: 2.12.0 (OHOS 适配版)
- Profile: ohos-aarch64 (os=OHOS, os.version=6.0, arch=armv8, compiler=clang 15)

## 验证结果

```bash
# conan-verify 结果
G0: PASS (预构建风险评估)
G1: PASS (配方完整性)
G2: PASS (conan create 成功)
G3: PASS (系统同名库隔离)
G4: PASS (产物完整性: bin/ 3文件, lib/ 18 .pm + 4 其他)
L2: PASS (smoke test: --help 正常)
L4: PASS (安全扫描: 0 个 ELF 文件)
L5: PASS (产物基线对比)
```

## 功能测试结果

### 模块加载 (18/18 PASS)
- Net::MQTT::Constants ✅ (MQTT_CONNECT=1, MQTT_PUBLISH=3)
- Net::MQTT::Message ✅ (依赖 Module::Pluggable，系统已安装)
- Net::MQTT::TopicStore ✅ (对象创建成功)
- 15 个消息类型子模块全部加载成功 ✅

### MQTT 消息编码/解码 (PASS)
- CONNECT 消息编码: 27 bytes, 首字节 0x10 ✅
- PUBLISH 消息编码: 24 bytes ✅
- new_from_bytes 解码: 正确还原 CONNECT 消息 ✅
- PingReq/PingResp: type=12/13, 2 bytes ✅

### TopicStore 功能 (PASS)
- add() 添加主题 ✅
- values() 通配符匹配 sensors/+ ✅

### 脚本 --help 测试 (3/3 PASS)
- net-mqtt-pub --help: EXIT=0 ✅
- net-mqtt-sub --help: EXIT=0 ✅
- net-mqtt-trace --help: EXIT=0 ✅

### 模块版本一致性 (PASS)
- 所有模块版本: 1.163170 ✅

详细测试报告: `reports/test-report.md`

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（纯 Perl 模块构建） |
| conandata.yml | 源码 + 补丁声明 |
| test_package/conanfile.py | Conan L1 测试（模块加载验证） |
| patches/0001-add-findbin.patch | FindBin + pod2usage + Net::Pcap 条件加载 |
| reports/conan-verify-report.md | Conan 验证报告 (全门禁 PASS) |
| reports/test-report.md | 功能测试报告 (模块加载 + 消息编解码 + 脚本) |
| reports/reviewer-report.md | 上库评估报告 (符合上库要求) |
| reports/conan-create.log | Conan create 日志 |
| reports/baseline.json | 产物基线 |

## 注意事项

1. **纯 Perl 模块**：本软件不含 C/C++ 代码，无需交叉编译，所有平台通用
2. **PERL5LIB 设置**：使用时需设置 `PERL5LIB` 指向包的 `lib/` 目录，或通过 Conan 的 `env_info.PERL5LIB` 自动设置
3. **net-mqtt-trace 限制**：该脚本需要 Net::Pcap 模块才能正常工作（抓包功能），当前环境未安装 Net::Pcap，仅 --help 可用
4. **与 perl-dbd-pg 的对比**：本软件为纯 Perl 模块，不受 SELinux HMDFS 限制影响（perl-dbd-pg 的 XS 模块需要管理员安装到系统目录）
---

**编译结束**: 2026-06-29 16:29
**最终状态**: published
