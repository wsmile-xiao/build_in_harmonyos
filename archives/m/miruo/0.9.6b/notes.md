# miruo 0.9.6b — 适配笔记

## 基本信息
- 上游：https://github.com/KLab/miruo （KLab，日本）
- 版本：0.9.6b（2012-12-25 发布的最终版本，tag tarball）
- 许可证：GPL-3.0-or-later（COPYING 为 GPLv3，源文件头 "any later version"）
- 构建系统：autotools（autoconf 2.67 / automake 1.11.1），产物为单一 CLI 二进制
- 源码构成：miruo.c（主程序）、lnklist.c/.h（链表工具）、miruo.h
- 依赖：libpcap（抓包），安装到 sbin/（Makefile.am 的 sbin_PROGRAMS）

## 上游与源码事实核查
- 官方 tag tarball `0.9.6b.tar.gz` sha256 =
  `0b31a5bde5b0e92a245611a8e671cec3d330686316691daeb1de76360d2fa5f1`
  （2026-09-20 下载验证；官方 URL 直连超时，经 gh-proxy.com 镜像获取，
  内容与 tag 一致，已按规则记录镜像列表）
- **上游打包缺陷（非适配问题，不 patch）**：0.9.6b tag tarball 的 configure 未重新生成，内嵌版本串仍是 0.9.6a ——
  `miruo -V` 输出 "miruo version 0.9.6a"。AC_INIT 里 PACKAGE_VERSION 是 0.9.6b，但 configure 未重跑。
  属上游缺陷，记录在此，patch 必须最小化故不修。
- 上游无测试套件：无 tests/ 目录、无 Test 段；`make check` 是 automake 空操作
  （仅输出 "make: 'check' is up to date" 之类，实际无测试运行）。Travis CI（.travis.yml）也只有 build，无 test 步骤。

## OHOS 适配
### 补丁（1 个，最小化）
`patches/0001-configure.patch` — configure 中创建 config.status 临时目录的
`umask 077` → `umask 022`（两处同一代码块，即 E011 标准修复）。

E011 背景：HMDFS 强制目录 setgid；`umask 077 && mktemp -d` 产生
`drwx--S---` 目录，即使属主也不可写，config.status 报
"can't create ./confXXXX/subs1.awk: Permission denied"。
知识库已有该条目（E011），直接引用，无需新增。

### 无需补丁的适配点
1. **AC_PROG_CC 不探测 clang**：autoconf 2.67 的 AC_PROG_CC 探测列表只有
   gcc/cc/cl.exe。OHOS profile 通过 conf `tools.build:compiler_executables`
   → AutotoolsToolchain 生成 CC=clang 环境变量，configure 直接采用，无需 patch。
   （exploration 时以 CC=clang 手工验证通过，探索产物正常。）
2. **sbin → bin 重定向**：上游 Makefile.am 用 `sbin_PROGRAMS`，安装到 sbin/。
   conan 惯例工具在 bin/。通过 AutotoolsToolchain 追加
   `--sbindir=${prefix}/bin` 实现，无需 patch。（本地探索安装确认只有
   miruo 一个程序、无 man/无额外文件。）
3. **/proc/self/statm**：miruo 运行时读取自身内存。已验证 HarmonyOS PC
   上 /proc 挂载且 statm 可读，无需处理。

### 构建要点
- make 必须 `-j1`：并行 make 在 HMDFS 上触发 jobserver fifo EPERM（E074），
  知识库已覆盖，直接引用。
- libpcap/1.10.6（ohpcd remote）包内仅 libpcap.a，静态链入 miruo。
  产物 NEEDED 仅 libc.so —— test_ohos.sh 断言这一点。

## 测试
- **上游测试：0**。上游无任何测试（无 tests/、make check 空操作、CI 无 test）。
- **OHOS 专项测试 1 个**：`test_package/test_ohos.sh`（9 条断言，fail closed，
  任何非零退出/超时/缺工具都判失败），覆盖：
  1. ELF class = ELF64、Machine = AArch64、Type = DYN（PIE）
  2. .interp == /lib/ld-musl-aarch64.so.1（musl，而非 glibc）
  3. 无 RPATH / RUNPATH（libpcap 静态链入，无需运行时搜索路径）
  4. 动态依赖仅为 libc.so（无 libpcap.so NEEDED）
  5. OHOS ELF 标记：.codesign ×1 + .note.ohos.ident
  6. 二进制内无本机构建路径（/storage/、/home/、/data/service/hnp、/build/）
  7. `miruo -V` 真实运行：打印版本横幅（上游缺陷实际打印 0.9.6a，断言格式）
  8. `miruo -h` 真实运行：打印 usage，不崩溃
  9. `miruo -i nonexist0` 真实运行：pcap 诊断 + 优雅退出 rc=1
  （7/8/9 附加 no_crash 检查：超时、信号致死、崩溃标记均判失败）

### 环境限制说明（真实尝试并保留错误证据）
- 实机运行 miruo 抓包需 root + 网络接口，本环境无法做真实抓包验证，
  已用 `-V`/`-h`/`-i nonexist0` 等不需权限的 CLI 行为替代验证（错误输出
  与退出码证据保留在 conan create 日志：`[ohos] 9/9` 输出块）。
- 上游无测试套件，无法执行上游测试，记录 0（`make check` 实测输出
  "Nothing to be done for 'check'"，退出码 0，无任何测试运行）。

### 最终构建与测试结果（2026-09-20）
- `conan create . -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b ~/.conan2/profiles/ohos-aarch64 --build=missing` 完整通过（rc=0）
- test_package 阶段输出：`OHOS ASSERTIONS PASSED: 9/9` + `ALL OHOS TESTS PASSED`
- 产物：`<pkg>/bin/miruo`，ELF64/AArch64/DYN(PIE)，.interp=/lib/ld-musl-aarch64.so.1，
  NEEDED 仅 libc.so，无 RPATH/RUNPATH，.codesign ×1 + .note.ohos.ident
- `miruo -V` → "miruo version 0.9.6a"（上游缺陷，见上）；`-h` rc=0 打印 usage；
  `-i nonexist0` rc=1 输出 pcap 诊断（"nonexist0: No such device..." 类）

## Conan recipe 说明
- package_type = "application"（CLI 工具，无库）
- settings 全四项；os 限定 Linux/OHOS（AF_PACKET、/proc 依赖）
- requirements: libpcap/1.10.6（static-only 包）
- generate(): AutotoolsDeps + AutotoolsToolchain，configure_args 追加
  `--sbindir=${prefix}/bin`
- build(): configure + make -j1
- package(): autotools.install()（sbindir 已重定向到 bin）
- test_package: VirtualRunEnv + test_ohos.sh（由 test() 直接以 bash 挂接执行，
  传入 <pkg>/bin/miruo 绝对路径，真实运行被测产物）

## 知识库判断（路径 A/B）
- **路径 A 全部命中，无路径 B**：
  - E011（configure umask 077 临时目录不可写）→ 现有知识库条目直接覆盖
  - E074（并行 make jobserver fifo EPERM）→ 现有知识库条目直接覆盖
  - sbin→bin 重定向：库内已有 arptables 等多个先例，属配方层面惯例，不是
    新的共性问题
- 未发现未覆盖且具跨库复用价值的新问题 → **未创建知识库扩展**（不硬凑路径 B）
