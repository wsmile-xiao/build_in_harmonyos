# msdl 1.2.7-r2

msdl（Media Stream DownLoader）是一个多媒体流下载命令行工具，支持
HTTP/FTP/RTSP/MMS/MMST/MMSH/SDP 协议，2010 年的纯 C 实现，仅依赖
libc 与 POSIX socket（无任何第三方库）。本包以 Conan application
形式打包（只产出 `bin/msdl`，无库、无头文件）。

## 源码

- 上游发布页: <http://msdl.sourceforge.net/>（SourceForge 官方 URL，
  与 Homebrew formula 记录一致；曾考虑 FreeBSD distcache 镜像，但其在
  本机网络环境下不可达——Fastly 边缘节点返回 421 / 证书 SAN 不匹配，
  已实证后弃用）
- 许可证: GPL-2.0-or-later。**以源文件头为准**：全部 24 个 `src/*.c`
  头部均为 "version 2 ... or (at your option) any later version"；
  顶层 `COPYING` 文件误放了 GPLv3 全文（上游打包错误，2010 年至今未修）。
  配方 license 字段取 GPL-2.0-or-later，`licenses/COPYING` 原样拷贝留证。

## OHOS 适配（路径 A 基础适配，零补丁文件）

全部适配在配方内联完成，`patches_applied: []`：

1. **E129 — configure umask（复用知识库既有条目，不新增）**
   HMDFS（HarmonyOS 分布式文件系统）对新建目录恒置 setgid 位。configure
   的 `(umask 077 && mktemp -d)` / 回退 `(umask 077 && mkdir)` 产生的
   临时目录模式为 `drwx--S---` —— 属主连 x 位都没有，config.status
   阶段 "could not setup config files machinery" 直接失败。
   修复：`configure` 内两处 `umask 077` → `umask 022`（replace_in_file）。
   已实证 VPATH 构建下 configure 生成的 config.status 自动继承 022，
   故只需替换 configure 一处文件。

2. **-fcommon（clang 15 默认 -fno-common）**
   2010 年代码在头文件里定义未初始化全局变量（display.h:76
   `colors_available`、display.h:92 `display_flags`、asmrule.h:56
   `symbols`、asmrule.h:77 `operators`、rmff.h:52 `prop_flags` 等），
   多个翻译单元 tentative definitions 合并成 ld.lld duplicate symbol。
   仓库先例：barcode/0.99 等同款。

3. **-fgnu89-inline（C99 inline 语义）**
   src/url.h:63 `inline int is_url_valid_char(...)` 只有 inline 定义、
   无分离 extern 定义；C99 inline 语义下无外部符号 → ld.lld undefined
   symbol。仓库先例：mlddc/1.0.1、bandwidthd、libmoe。

native 编译（构建机即 HarmonyOS PC），不传 `--build/--host/--target`
三元组；configure 自带 config.guess 识别为 aarch64-unknown-linux-ohos。

## 上游测试

上游不提供自动化测试：`src/Makefile.am` 无 `TESTS`/`check_PROGRAMS`，
无 tests/ 目录。`make check` 实际执行（EXIT=0）但零测试目标——输出无
"Checks" 段，直接完成。**上游测试数 = 0**（如实记录，未虚报）。

## test_package（L1 + HarmonyOS 专项）

`test_package/test_msdl.c` 三项测试，全部真机实际执行：

1. **L1 基础**: fork+exec 包内 `msdl`（无参数），验证打印 usage 且
   退出码 1（2010 年代码的预期错误路径，证明可执行、动态链接正常）。
2. **HarmonyOS 专项·ELF/动态依赖**: 进程内解析 ELF —— ELF64/LSB/
   EM_AARCH64、PT_INTERP 为 `/lib/ld-musl-aarch64.so.1`（musl 目标
   环境）、DT_NEEDED 仅 `libc.so`（上游零外部依赖的直接验证）。
   不依赖 host 侧 readelf，CI 环境自包含。
3. **HarmonyOS 专项·真实网络行为**: 进程内极简 HTTP 服务器
   （bind 127.0.0.1:0 内核分配端口，fork 服务循环），msdl 真实发起
   HTTP 下载 64 KiB 确定性伪随机数据，逐字节比对内容一致。覆盖
   socket 连接、GET 请求、响应解析、写盘全链路，以及 msdl 先探测
   mmsh、再 fallback http 的真实行为（dl.log 证据）。退出码矩阵中
   无参/-V/--help/坏 scheme/连接拒绝均为 1，下载成功为 0，已在
   build-probe3 与 vprobe3 实证。

## 复现

```bash
conan create archives/m/msdl/1.2.7-r2 \
  -pr:h ~/.conan2/profiles/ohos-aarch64 \
  -pr:b ~/.conan2/profiles/ohos-aarch64 \
  --build=missing
```

（本机即 HarmonyOS aarch64 PC，native 构建；profile 使用
`~/.conan2/profiles/ohos-aarch64`，clang 15.0.4 默认 target
aarch64-unknown-linux-ohos。）

## 知识库判断

- E129 修复**复用**既有条目（E129.kv），未新增知识条目。
- `-fcommon`/`-fgnu89-inline` 为 flag 级方案且仓库已有多个配方先例，
  知识库无 C99 inline / -fno-common 专项条目，亦不新增（满足“无现成
  完整方案且可复用时才新增”的反向条件）。
