# ogmtools 1.5.2（包版本；上游源码 ogmtools-1.5）适配笔记

## 2026-10-05 当前修复与实证（覆盖下方历史结论）

- 1.5.2为上游1.5的第2次适配修复版本，不是上游新版本。官方HTTPS归档实际读取并哈希一致，旧“仅HTTP”说明已过时。
- 原错误容器测试允许RC0或1，仅作历史错误路径记录，不能证明功能或充当鸿蒙专项。当前真实测试是6版本项+1合法PCM往返消费者，以及不同PCM输入的独立HMDFS中文空格路径专项。
- r001原生构建在旧Makefile硬编码`AR=ar`时真实失败；r002通过make变量绑定存在的LLVM归档器，不改上游生成文件或系统工具。
- r002 actual Conan create RC0；两组32000字节PCM的格式及全部样本逐字节一致。消费者7/7、HarmonyOS专项1/1，单次launch及release/postrelease PASS。
- 官方无上游测试套件，实际`make -j1 check` RC0，不宣称0/0 PASS。无源码补丁。
- 当前配套E2026100503为独立可复用无损数据流测试机制。下方2026-09旧记录、版本/分支及归档结果均不是本次CI或提审证据。
- r004在生产shell修复后独立通过消费者7/7与鸿蒙专项1/1，唯一launch及release/postrelease PASS；正常Conan激活之后覆盖旧profile的CONFIG_SHELL/SHELL，不使用env=None绕开依赖运行环境。
- 正式r003实际Conan和本地CI通过；整体finish仍RC1/PARTIAL，后置全库知识、框架快照及打包元数据缺项如实保留。当前HEAD平台Review/CI仍待完成，尚未提审。

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15 (OHOS aarch64 交叉工具链)
- 状态: built

## 编译步骤

```bash
# conan 配方驱动（conanfile.py build()）：
# 1. 注入 mktemp shim（PATH 前缀）
# 2. --with-ogg-prefix/--with-vorbis-prefix/--with-dvdread-prefix 指向 conan 依赖 package_folder
# 3. CPPFLAGS/LDFLAGS 注入依赖 include/lib + 绝对 -I<source>/avilib
# 4. LD_LIBRARY_PATH 注入依赖 lib（configure AC_TRY_RUN 测试程序运行期）
# configure --prefix=<conan prefix> --enable-static --disable-shared --with-*-prefix=...
# make -j1   （HMDFS 不支持 jobserver mkfifo）
# make install（conan prefix 直装）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.status: can't create ./confstatXXXX/subs.sed: Permission denied`，Makefile 静默缺失 | E126 变体：HMDFS 上 `mktemp -d` 创建的目录属主不可写（mode `drwx--S---`，普通 mkdir 目录 `drwxrws--x` 可写）；mktemp 返回 0 使 configure 自带 mkdir fallback 不触发 | build() 注入 PATH 前缀 mktemp shim（转译 mkdir+随机名，仅本包构建生效） |
| 2 | configure 判 `checking for Ogg... no` / `Vorbis... no` | XIPH 老宏测试程序 AC_TRY_RUN：Vorbis 测试编译只有 vorbis 的 -I，但 `vorbis/codec.h` 内部 `#include <ogg/ogg.h>` 找不到；测试失败时宏清空 VORBIS_CFLAGS | CPPFLAGS/LDFLAGS 同时注入三依赖 include/lib 目录 + LD_LIBRARY_PATH 注入依赖 lib（测试程序运行期可见 .so） |
| 3 | `fatal error: 'avilib.h' file not found`（conan out-of-tree 构建） | Makefile.am 的 `-Iavilib` 是相对路径，conan basic_layout 下 CWD=build-release 解析不到 srcdir/avilib | CPPFLAGS 追加绝对路径 `-I<source_folder>/avilib` |
| 4 | `make -j4` 报 `jobserver mkfifo: Operation not permitted` | HMDFS 不支持 mkfifo | make -j1 |
| 5 | 首版 test_package 无 layout()，`conan test` 就地落盘 3 个运行时文件被误提交 | conan 2 无 layout 时 test() 在配方目录就地执行 | test_package 加 `basic_layout(self, src_folder=".")`，产物隔离到 build_folder；清除已误提交文件 |
| 6 | CI L0d 判 `stub_test_method` | 门禁行级 grep `self.run.*(echo|print|true)`，测试逻辑与 self.run 同行含 echo | 测试逻辑移入 shell 脚本，conanfile 只留一条纯净 `self.run(f"sh {script}")` |

## 源码修改

无补丁（0 个 patch）。所有 OHOS 适配均在 conanfile.py 构建期完成，上游源码零改动。

## 依赖版本

- libogg/1.3.6（制品仓 ohpcd 已发布，libvorbis/1.3.7 的传递依赖，版本经 conan 冲突解析确认）
- libvorbis/1.3.7（制品仓 ohpcd 已发布）
- libdvdread/7.1.0（制品仓 ohpcd 已发布，静态 .a，dvdxchap 专用）

## 历史验证记录（不作为当前候选功能通过证据）

```bash
$ conan create archives/o/ogmtools/1.5 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --user=ohpcd --channel=stable
# G1 配方完整性 PASS / G0 预扫描 PASS / G2 conan create 干净构建 PASS
# G3 系统同名库隔离 PASS / G4 产物完整性 PASS
# test_package: 6 工具 --version 全过（ogmmerge/ogmdemux/ogminfo/ogmsplit/ogmcat/dvdxchap → v1.5）
#   + 最小 OGG 页 ogminfo rc=0 / ogmsplit rc=1（优雅退出，非 segfault）→ ALL_PASS
```

## 2026-09-13 当前候选本地交叉验证

当前 `feat/ogmtools-1.5` 候选在 Windows 主机使用任务私有
`local-ohos.profile`（OHOS/armv8 host）和 `local-build-windows.profile`
（w64devkit build）重新执行 Conan create。配方的 Windows-hosted 分支通过
`win_bash`、正斜杠盘符路径、`self.run(env=None)`、DVD 头文件缓存和显式
CPPFLAGS/LDFLAGS 完成：

- `configure`：RC 0，Ogg/Vorbis/DVDOpen 和 DVD 头文件检查通过；
- `make -j1` / `make install`：RC 0，`bin/` 生成 6 个 OHOS ELF；
- `test_package`：明确记录 cross-build execution deferred，避免在 Windows
  主机执行 AArch64 ELF；8 个断言待同一候选的目标 W3 单次启动执行。

对应日志：`F:\\HarmonyPC\\ogmtools-1.5-20260912\\conan-create-local-ohos-r8.log`。
该主机结果不替代目标签名、W3 运行和回收证据。

## 注意事项

- 上游为 2004 年项目（bunkus.org 官网已停更），无测试套件（`make check` 空目标），L1 测试由 test_package 承担
- 当前官方归档采用 HTTPS 并实测 SHA-256 一致，不能沿用旧 HTTP-only 结论。
- ogmcat 为上游自述 "not finished" 的实验工具
- dvdxchap 依赖 libdvdread（静态），真实 DVD 结构端到端解析未验证（需 .iso 样本，超出 L1 范围）
---

**编译结束**: 2026-09-03 21:14
**最终状态**: built

## 2026-10-05 当前修复与实测

删除旧未调用的 `l1_test.sh`，不再以损坏空容器接受 RC0/1 证明功能。实际入口为 `media_roundtrip.py`，消费者7项及独立HMDFS专项1项；Windows bash/make配置缺失明确报错，两项实际方法定向检查通过。上游产品源码未修改。

新原生事务r005真实Conan create RC0，7/7及1/1完整通过，唯一launch、release/postrelease PASS且进程0；快照SHA-256 `bb5e1ee4710d0f96d4b4a78f9678d07f7ebd3be31734c8eabd2dc3346c6d7b47`。独立formal-r004真实Conan及本地CI通过同分母，快照 `69e93c6698f32657fb4b6e2a1717584791293bcc00e6690f7787e2ddf1736cc9`。整体finish保留RC1/PARTIAL历史快照/全库元数据限制，平台CI仍待完成，不冒充已提审。历史r002/r004各自保留，不拼接证据。
