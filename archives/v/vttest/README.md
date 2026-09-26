# vttest

**VT100/ANSI 终端测试程序** — 在被测终端上运行，菜单驱动地向终端发送转义序列
与测试图案，检查光标移动、字符集、双宽/双高、颜色、键盘/鼠标报告、设备应答、
VT52/VT220/VT320/VT420/VT520 与 xterm 扩展等行为是否符合 DEC/ANSI 规范。

- 上游主页：<https://invisible-island.net/vttest/>
- 源码归档：<https://invisible-island.net/archives/vttest/>
- 许可证：MIT（COPYING，Thomas E. Dickey, 1996-2025）

## 提供的能力

| 命令 | 说明 |
| --- | --- |
| `vttest` | 在当前终端上运行菜单式 VT100 兼容性测试（`-V` 打印版本；`-c cmdfile` 回放录制的操作命令；`-l` 记录测试日志） |

典型用途：终端模拟器/串口终端/控制台驱动的兼容性回归；比较不同终端对
DEC 私有序列与 ANSI 颜色序列的实现差异；生成可复现的测试操作脚本。

## 版本

| 版本 | 状态 | 说明 |
| --- | --- | --- |
| 2.7-20251205 | built | 首次适配；上游无自动化测试（vttest 本身即终端测试工具，N=0），本适配在 test_package 补全消费者回归 + PTY 交互冒烟 |

上游 `patchlev.h` 标识 `RELEASE 2 / PATCHLEVEL 7 / PATCH_DATE 20251205`，
发行 tarball 名为 `vttest-20251205.tgz`，Conan 包版本记为 `2.7-20251205`。

## 构建

```bash
conan create archives/v/vttest/2.7-20251205 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

产物：`bin/vttest`、`share/man/man1/vttest.1`、`licenses/COPYING`。

## OHOS 适配要点

- **config.guess 不识别 HarmonyOS 内核**：上游 `config.guess`（2025-07-10）的
  `case $UNAME_SYSTEM` 只认 `Linux|GNU|GNU/*`，而 HarmonyOS PC 的 `uname -s`
  返回 `HarmonyOS`，configure 直接以 `cannot guess build type; you must
  specify one` 退出；同一脚本的编译器探测临时目录还用 `umask 077`。
  补丁 `patches/0001-config.guess.patch` 增加 `aarch64:HarmonyOS:*:*` →
  `aarch64-unknown-linux-$LIBC` 映射并把三处 umask 放宽为 022，使原生构建
  无需 `--host` 即可完成（上游 config.sub 已能识别 `linux-ohos`，如需显式
  传 host 三元组也可行）。
- **configure umask 补丁（E129/E112/E136）**：HMDFS 对 `umask 077` 新建目录
  强制 setgid，得到 `drwx--S---`，owner 也无法写入；autoconf 生成的
  configure/config.status 用 `(umask 077 && mktemp -d "$TMPDIR/csXXXXXX")`
  建临时目录，会以 `could not setup config files machinery` 失败。补丁
  `patches/0002-configure.patch` 把两处 `umask 077` 改为 `umask 022`
  （与已合入的 a52dec/0.7.4、teseq/1.1.1 同款）。
- **无 C 源码修改**：不改 C 源码、不注入 `__OHOS__`。
- **上游测试为 N=0**：vttest 是被测终端的交互式测试工具，上游不提供自动化
  用例与预期输出基准（清点证据见 2.7-20251205/test_package/MANIFEST.yml）。
  本适配在 `test_package/` 补全 9 条消费者断言（6 条 CLI + 3 条 PTY 交互
  冒烟），由 `conan create` 在目标上真实执行。

详细的适配过程与问题清单见 [2.7-20251205/notes.md](2.7-20251205/notes.md)。
