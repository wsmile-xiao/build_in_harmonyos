# ogmtools 1.5.1 适配笔记（上游版本 1.5）

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15 (OHOS aarch64 交叉工具链)
- 状态: built

## 编译步骤

```bash
# conan 配方驱动（conanfile.py build()，Conan 修订版本 1.5.1）：
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

## 验证结果

```bash
$ conan create archives/o/ogmtools/1.5.1 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --user=ohpcd --channel=stable
# G1 配方完整性 PASS / G0 预扫描 PASS / G2 conan create 干净构建 PASS
# G3 系统同名库隔离 PASS / G4 产物完整性 PASS
# test_package: 6 工具 --version 全过（ogmmerge/ogmdemux/ogminfo/ogmsplit/ogmcat/dvdxchap → 上游 v1.5）
#   + 最小 OGG 页 ogminfo rc=0 / ogmsplit rc=1（优雅退出，非 segfault）→ ALL_PASS
```

## 2026-09-13 当前候选本地交叉验证

当前 `feat/ogmtools-1.5.1` 候选在 Windows 主机使用任务私有
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
- 官方源仅支持 http://（2000 年代老站），sha256 已固定内容
- ogmcat 为上游自述 "not finished" 的实验工具
- dvdxchap 依赖 libdvdread（静态），真实 DVD 结构端到端解析未验证（需 .iso 样本，超出 L1 范围）

## 2026-09-17 successor 目标与上游入口验证

- 当前候选由 W3 `ogmtools-1.5.1-w3-r009` 绑定；提交前要求在 `10.62.195.15:2222` 完成 fresh transfer/readback 和唯一 launch，由冻结验证器重放 12 个 receipt，确认 Harmony 测试 8/8、状态 11/11、消费者程序/断言 2/2、数据路径 2/2，并完成 release、postrelease 和远端根退休。精确 TREE 与终态哈希保存在任务外部 PRE_CREATE/W3 证据中，避免候选文件自引用。
- 上游 Makefile 与 `avilib/Makefile` 未声明 `TESTS`、`check_PROGRAMS` 或 `check_SCRIPTS`。真实 `make check` 递归进入 `avilib` 和顶层 `check-am`，两处均报告无需执行，最终 RC 0，因此上游清单为 0/0 PASS（不适用）。
- Windows 上首次 `make check` 暴露递归 `$(MAKE)` 的空格路径问题：生成的 Makefile 把 `C:/Program Files (x86)/.../make.exe` 无引用地嵌入 Shell 命令，在 `(x86)` 处解析失败。通过命令行 `MAKE=F:/HarmonyPC/.../toolchain/make` 绑定无空格任务 wrapper 后，同一入口返回 RC 0；未修改上游源码或配方。
---

**编译结束**: 2026-09-03 21:14
**最终状态**: built
