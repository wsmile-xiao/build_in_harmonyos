# acpid 2.0.34 — 新库可行性验证（probe_only_no_upload）

> 档案创建时间: 2026-08-04 17:35
> 最后更新: 2026-08-04 18:05
> 当前状态: ✅ 本地全链路通过（probe 模式，未上传）
> executor: pc2-2 | 策略: probe_only_no_upload | 远端授权: 无

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | acpid（ACPI event daemon） |
| 版本 | 2.0.34 |
| 构建系统 | autotools（configure/make，configure 预生成） |
| 许可证 | GPL-2.0-only |
| 上游 | https://sourceforge.net/projects/acpid2/ |
| 源码镜像 | https://deb.debian.org/debian/pool/main/a/acpid/acpid_2.0.34.orig.tar.xz（实测可用） |
| sha256 | 2d095c8cfcbc847caec746d62cdc8d0bff1ec1bc72ef7c674c721e04da6ab333 |
| 包类型 | application（daemon + acpi_listen + kacpimon，无库） |
| 第三方 conan 依赖 | 无（仅 libc / 内核头文件） |

## 二、环境探测（鸿蒙主机特有约束）

| 检查项 | 结果 |
|--------|------|
| 内核 | HarmonyOS HongMeng Kernel 1.12.0 aarch64 |
| /tmp 只读 | ✅ 确认只读 → 全程使用 TMPDIR=/data/storage/el2/base/.acpid-tmp |
| HMDFS | ✅ /storage/Users/currentUser 为 hmdfs（umask 077 临时目录不可写）→ 构建转移到 tmpfs |
| 编译器 | clang 15.0.4（无 gcc），CC=/data/service/hnp/bin/clang |
| conan | 2.29.1（OHOS 适配版），profile ohos-aarch64 |
| SELinux/内核能力 | setreuid/chroot 等未实测（daemon 运行依赖） |
| 签名 | ELF 产物待 sign-elf（发布环节） |

## 三、ACPI 接口探测（关键证据，全部缺失）

```
uname -a: HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Wed Apr 29 10:16:03 UTC 2026 aarch64 GNU/Linux
/proc/acpi   → No such file or directory
/sys/bus/acpi → No such file or directory
netlink probe → 无 NETLINK_GENERIC 相关输出
```

**结论**：HarmonyOS PC 内核未提供 Linux 标准 ACPI 接口（/proc/acpi、/sys/bus/acpi、ACPI netlink）。acpid 是纯事件源 daemon，编译期不依赖这些接口（configure/make 全通过），但**运行期无事件源可用**——这是 HarmonyOS 系统差异，指向**路径 B 候选（HarmonyOS 系统差异专项）**。

## 四、编译验证（conan create 通过）

- **G2 conan create: PASS**（日志：reports/conan-create.log）
- 产物 3 个 ELF（arm64, musl, libc.so 动态依赖）：
  - sbin/acpid（84416B）
  - sbin/kacpimon（22448B）
  - bin/acpi_listen（31104B）
- `acpid --version` → `acpid-2.0.34`，exit 0
- `acpi_listen --help` → usage，exit 0

### 真实错误与修复（按出现顺序）

1. **E007 config.guess 无法识别 HarmonyOS**：`checking build system type... unable to guess system type`
   - 修复：补丁 0001-build-aux-config.guess.patch（config.guess 新增 HarmonyOS 分支 → `*-unknown-linux-ohos`，config.sub 接受 ohos*/linux-ohos*）
2. **HMDFS umask 077 权限问题（两次）**：
   - config.guess 的 `$TMPDIR/dummy.c: Permission denied`（TMPDIR 指向 hmdfs 的 $HOME/tmp 时）
   - `config.status: ./conflBPH30/subs1.awk: Permission denied`（build 目录在 hmdfs 上）
   - 修复：TMPDIR 指向 tmpfs（/data/storage/el2/base），并仿 sed 配方将整个 configure/make 转移到 tmpfs 构建
3. **E091 sockaddr_storage 重定义**：OHOS sysroot 的 linux/socket.h 与 sys/socket.h 同时定义 `struct sockaddr_storage`
   - 修复：CFLAGS 加 `-D__MUSL__`（触发 sys/socket.h 的 `#ifndef __MUSL__` 守卫）——与 bird2/libkcapi/fastfetch 同源方案
4. **conan self.run 双引号嵌套 bug（本地开发修复）**：`bash -c "..."` 外层双引号内嵌 env 的 `CFLAGS="..."` 导致 configure/make 未真正执行却返回 0
   - 修复：bash -c 外层改用单引号

## 五、测试核验

- 上游：**无自动化测试**。仅有手写 TESTPLAN（人工验收文档，描述电源键/合盖事件等手动步骤），无 test/ 目录、无 make check 目标
- 新增 smoke test（test_package/test.sh，**2/2 PASS**）：
  - `acpid --version` → `acpid-2.0.34`（返回 0）
  - `acpi_listen --help` → usage（返回 0）
- test_package 说明：acpid 是 daemon 非库，无法调 API，采用**可执行文件验证方案**（替代验证思路），并在 MANIFEST.yml 中声明
- 测试规模：上游 0/0（N/A，无测试用例）；新增 2/2 PASS

## 六、依赖检查

- 无第三方 conan 依赖（configure.ac 仅标准 libc 函数检查）
- 无需【依赖项】issue

## 七、路径判断取证

- **路径 A 候选**：编译 + conan create + conan-verify 全通过 ✅
- **路径 B 候选（HarmonyOS 系统差异）**：ACPI 接口（/proc/acpi、/sys/bus/acpi、netlink）在 HongMeng Kernel 1.12.0 上全部缺失，acpid 运行期无事件源 → 真实系统差异证据已记录
- **测试框架/工具链专项（10 分候选）**：上游无自动化测试，补写 2 个 smoke test 并 PASS，测试规模已说明
- 是否与其他专项重复：E007（config.guess）与 E091（sockaddr_storage）均为知识库已有模式（sed/bird2/libkcapi 已沉淀），ACPI 接口缺失为本次新发现，需查重后确认
- Wiki 状态：probe_only_no_upload 阶段不提交 wiki，只记录证据

## 八、当前状态

- probe_only_no_upload：**未 push、未 submit、未 /ai review**
- 本地 9 项门禁（probe 范围）：编译 ✅ / 上游测试核验 ✅（无测试，真实记录）/ 新增测试 ✅ 2/2 / 依赖 ✅ / conan create ✅ / conan-verify ✅
- finish/W3/submit 属上传链路，按 probe 策略不执行
