# morse 2.7 适配笔记（OHOS AArch64 / Conan 2）

## 上游身份核验（防同名项目混淆）

“morse” 同名软件众多（如 NP2/morse.py、jopen/morse 等），必须锁定
正确官方上游。核验链（2026-09-01）：

| 项目 | 值 |
|---|---|
| 名称 | **Morse Classic**（Eric S. Raymond） |
| 官方主页 | http://www.catb.org/~esr/morse-classic |
| 官方仓库 | https://gitlab.com/esr/morse-classic |
| 2.7 release | NEWS 首条：2026-03-17 "morse 2.7: Raise the system quality bar" |
| 官方源码 URL | https://gitlab.com/esr/morse-classic/-/archive/2.7/morse-classic-2.7.tar.gz |
| SHA256 | `61d6ddaf2365fb767f321a13a0bed82d96e5729e396a4ca5914d207819efd1b0` |
| License | BSD-2-Clause（COPYING：BSD LICENSE，(c) Eric S. Raymond） |
| 功能 | morse（文本→莫尔斯码：蜂鸣+屏幕点划+随机练习）+ QSO（模拟业余无线电报文生成器） |

源码核验与 URL 切换（2026-09-01 取证，2026-09-02 定稿）：

- **CATB tarball**（http://www.catb.org/esr/morse/morse-2.7.tar.gz）：
  curl 多次下载字节一致（47093 字节，sha256
  `6ae4a76fc5aa57a520dca38380676142fd427a1748501a71cadd352c3f187fe3`）；
  `file` 为 gzip 压缩数据，`tar -tzf` 正常，解压 38 文件。
- **CI 实收 48fc 之谜**：conan 实际下载 184320 字节、sha256
  `48fc1b2b4656dad804caf7f912e86e3c50b393890c8cf16b5172982da902f236`，
  精确等于 `gunzip(6ae4 tarball)` —— catb.org 响应携带非标准
  `content-encoding: x-gzip` 头，conan 的 requests/urllib3 下载器
  将其透明解压为纯 tar（curl 不解析该头，得到原始 6ae4...）。
  CATB 的 .tar 变体同样带 CE 头，https 端点证书主机名不匹配 ——
  CATB 侧无干净稳定的机器可获取方式。
- **GitLab 2.7 tag archive**（现用源）：tag 2.7 → commit
  `2af424ba1a1222e93f9c492b5f350b07495ed456`（"Tagged for
  external release 2.7"）；GitLab 无 release 附加产物（releases=0），
  tag archive 即官方源码归档；响应无 content-encoding 头，两次
  独立 curl 下载 + requests（conan 同路径）字节全同（49429 字节，
  sha256 `61d6ddaf2365fb767f321a13a0bed82d96e5729e396a4ca5914d207819efd1b0`）。
- **两源逐文件比对**：36 个共有文件（全部源码、Makefile、NEWS、
  COPYING、test_input、morse.xml 等）cmp 全同；差异仅打包层面：
  CATB 独有 xmlto 生成的 man 页 morse.1/QSO.1（构建产物，非源码），
  GitLab 独有 .gitignore/control/morse-logo.png（仓库维护文件）。
  源码内容完全一致，配方据此切至 GitLab archive。

## 零 patch

上游源码零修改。OHOS 构建的三个环境差异全部通过 make 变量 /
LD_PRELOAD 处理：

1. **OHOS SDK clang wrapper 常注 `-Wl,--code-sign`**：纯编译
   （-c）调用在 -Werror 下报 unused-command-line-argument。
   → `CFLAGS="-Wno-unused-command-line-argument"`。
2. **clang 15 对 1990s K&R 原型的严格化**：`static void die(),
   suspend();` 触发 -Wdeprecated-non-prototype / -Wno-gcc-compat。
   → 同上经 CFLAGS 追加 `-Wno-deprecated-non-prototype
   -Wno-gcc-compat`（不改源码，等价 GCC 10 时代的 gnu89 语义）。
   另附 `-std=gnu89` 明确语言模式。
3. **DEVICE 选择**：上游 Makefile 支持 X11/OSS/PA/ALSA/Linux，
   配方用 `make DEVICE=Linux`（仅依赖 libc/libm，无需音频栈）。

## 上游正式测试：make check（真实执行）

上游归档自带正式自测（README 明示 "Run \"make check\" to build
and self-test the software"）：

```
check: morse QSO testmorse testqso
testmorse: (cat test_input; qso.d/QSO) | ./morse -w 24 -l -e
testqso:   qso.d/QSO | ./morse -w 20 -l -e
```

- test_input：完美全字母句 + 数字测试 + VVV 结尾。
- 两目标在配方 build() 中**原样真实执行**（exit 0）：
  testmorse ≈210s、testqso ≈215s（-w 24/-w 20 真实 SIGALRM 节奏）。
- 无其它测试设施（无 ctest/gtest/autotools，gitlab CI 无独立工作流）。

### 音频路径的 console shim（构建期专用，不进产物）

morse 的 DEVICE=Linux 后端无条件 `open("/dev/console")`（PC 喇叭）
并用 KDMKTONE 发音。OHOS：
- 无 PC 喇叭设备；
- /dev/console 存在但普通用户无写权限（实测 "You have no
  permissions to use /dev/console (chmod a+w). Can't access
  speaker." → exit 1）。

处理：配方在**构建目录**内联一段 ~20 行 LD_PRELOAD shim（C 源码
内嵌于 conanfile.py），仅把 `open("/dev/console")` 重定向到
/dev/null；ioctl 返回值上游本就不检查，SIGALRM 计时/解码/全部
stdout 输出为真实路径。shim 绝不进入 package()（仅存在于
build_folder），test_package 同法使用。这不属于 patch：上游源码
零字节改动。

## OHOS AArch64 ELF 证据（本机真实执行）

构建机本身即 aarch64 OHOS（uname -m = aarch64），产物为：
- ELF64 / AArch64 / PIE（EXEC→DYN，因 wrapper 注入
  --code-sign-allowable 或 -pie）
- INTERP: `/lib/ld-musl-aarch64.so.1`（musl）
- 工具链三元组 aarch64-unknown-linux-ohos（clang 15.0.4，
  sysroot aarch64-linux-ohos，`-fuse-ld=lld`）
- 两二进制均在本机真实运行（真实解码 + 精确输出，见 test.sh）

## test_package 设计（基于上游源码语义，不猜参数）

morse(1)/morse.c 实测语义（详见 test.sh）：
- `-m`：屏幕输出点划（`... --- ...`），`-e`：省略结尾 <SK> 尾音，
  `-w N`：N wpm，`-l`：字母与点划同行滚动（`S... O--- S...`），
  `-c`：man 页官方语义 "complain about illegal characters instead
  of just ignoring them"（实测：非法字符输出 8 点错误符号
  `........`，exit 仍为 0）。
- 非法字符（如 `%`）：默认静默忽略；`-c` 下打错误符号——唯一
  exit 1 的输入错误路径是 `-C` 空字符集（`Error: -C charset
  selects no valid characters.`）。
- 未知选项（`-Z`）：stderr `unrecognized option: Z` + `Type
  "morse" without arguments to get self-doc` + exit 1（无独立
  --help；self-doc 仅 tty 交互时出现）。
- QSO：结构化报文（首行/尾行呼号对相同：`X de Y`，可含 `/5`
  后缀；RST 行有 8 种随机格式，分隔符 `=`/`/`/`,`；`+%` 结束行）。
  **行数随机（实测 13–17 行）**，只能断言结构而非固定行数；
  srand(time(0)) 同秒确定。

断言覆盖：文本→Morse 精确字节输出（SOS / SOS PARIS / 数字 123 /
长句 7 行 + 首词精确点划，cmp 比对）、字母滚动、负向（-C 空字符
集、未知选项 -Z）、QSO 结构（呼号回显/RST/+%/行数下限）、无参数
非 tty 静默、stderr 洁净性。全部为精确输出/精确退出码断言
（cmp / `[ = ]` / grep -E），无 `|| true` / ignore_errors /
无条件 OK。

test.sh 断言计数：t() 退出码断言 × 11 + check() 输出断言 × 17
= **28 项**（CI L4 实际运行：TOTAL=28 PASS=28 FAIL=0 SKIP=0）。

## 安装布局

对齐上游 `make install` 的 BINDIR：bin/morse、bin/QSO。man 页
不随包分发：GitLab tag archive 不含预生成的 morse.1/QSO.1
（CATB tarball 中为 xmlto 构建产物，上游源为 morse.xml；OHOS
构建机无 xmlto/xsltproc/docbook 工具链，CI 亦不检查 man 页；
conan copy() 对不存在的 pattern 静默跳过，package() 不受影响）。
commands.json 声明两个 CLI。

## 已知限制

- 音频后端固定 DEVICE=Linux（console）。OHOS 无 PC 喇叭，声音
  输出实际不可闻；解码/计时/屏幕输出全功能可用（这正是
  无头 CI 环境的预期形态）。
- morse 无 --version/--help 文本输出（self-doc 为 tty 交互式）；
  测试以 usage 错误路径与真实转换输出代替。
