# wren-cli 0.4.0 · 真机验证报告（任务 #11988 / 分支 feat/wren-cli-0.4.0）

## 环境

| 项 | 值 |
|---|---|
| 设备 | HarmonyOS PC（aarch64 / armv8，Toybox + mksh，HMDFS `/storage`，`/tmp` 只读） |
| profile | `ohos-aarch64`（harmonybrew SDK clang 15，libc++，`-target aarch64-linux-ohos`） |
| conan | 2.29.x（`conan --version` 见下方日志首行） |
| CONAN_HOME | `~/work/psj/ch-wcli11988`（本会话隔离副本，只拷 profile，未写共享 `~/.conan2`） |
| 工作目录 | `~/work/psj/wcli11988` |
| 命令 | `conan create archives/w/wren-cli/0.4.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing` |
| 完整日志 | `~/work/psj/wcli11988-ch1.log`（剥色取证 `.plain` / `.evidence`）、`~/work/psj/wcli11988-negative.log` |

## 上游坐标

```
https://codeload.github.com/wren-lang/wren-cli/tar.gz/refs/tags/0.4.0
200 / 522379 B / sha256 fafdc5d6615114d40de3956cd3a255e8737dadf8bd758b48bac00db61563cb4c
```
同一 sha256 也在 `https://github.com/wren-lang/wren-cli/archive/refs/tags/0.4.0.tar.gz` 上实测得到（两个归档生成器字节一致）。

## 结果

```
CREATE_EXIT:0
test/unit          ->  All 52 tests passed!
util/test.py       ->  All 92 tests passed (216 expectations).
                        Skipped 3 tests:            （上游自身的 // skip: 标记）
test_package       ->  TOTAL=36 PASS=36 FAIL=0
```
上游期望数对账：`test/` 全树 `// expect:` + `// expect runtime error:` 共 **220** 行；其中 3 个 `// skip:` 文件贡献 4 行（1+2+1）、5 个 `// nontest` 模块夹具贡献 0 行 → 实际执行 **216** 行，与运行器自报一致。
文件级：`test/` 95 个 `.wren` − 5 个 nontest − 3 个 skip = 87，加 `example/` 8 个中可离线运行的 5 个 = **92** ✓

## 交付物身份

```
包内顶层        : bin conaninfo.txt conanmanifest.txt licenses       （无 lib/ 无 include/）
bin/wren_cli    : 235968 B，e_machine = b700（EM_AARCH64）
sha256          : 4509e28f178eab08fdbda0ac4027beae996a9e63c17870752b6329f9c576d923
NEEDED          : libuv.so.1, libc.so
RUNPATH         : .../ch-wcli11988/p/libuve6966fe2b5f01/p/lib : .../p/wrenb4bc4f9317d3f/p/lib
licenses/LICENSE: 存在（MIT）
recipe revision : wren-cli/0.4.0#3cc0ce475889baf76956225bcf85a930
package id      : 43e210363adc57eece84b1f53b3e2d5b5ff0d93b
```
`RUNPATH` 是本库的关键适配点：`libuv` 发布的是 shared，`libuv.so.1` 只在依赖包目录里。没有 RUNPATH 时（第一、二轮实测）真机报
`Error loading shared library libuv.so.1` + 一串 `Error relocating ... uv_*: symbol not found`，
消费者套件 `TOTAL=30 PASS=3 FAIL=27`；烧进 RUNPATH 后 `Error relocating` 次数 = 0。

## L1e 破坏性反向验证（R34，正-反-正）

| 步骤 | 结果 |
|---|---|
| 正向（包内产物齐备） | `POS_EXIT:0`，`TOTAL=36 PASS=36 FAIL=0` |
| 反向（把 `$PKG/bin` 整体移出包目录后 `conan test`） | `NEG_EXIT:1`，首条即 `[FAIL] wren_cli is installed and executable`，`TOTAL=1 PASS=0 FAIL=1` |
| 还原 | `RESTORED_EXIT:0`，`TOTAL=36 PASS=36 FAIL=0` |

消费者套件断言的是**安装后的** `bin/wren_cli`，因此破坏 `bin/` 立刻变红 → 不是恒真断言。

## 上游平台行为的两条实测固化（非绕过）

1. `Directory.delete` 删**非空**目录：上游 `io.c` 走 `uv_fs_rmdir` + `handleRequestError`，
   实测 rc=**70**（EX_SOFTWARE），stderr 首行为 `uv_strerror` 文本 `directory not empty`，
   后跟 `[scheduler] / [io] / [脚本]` 共 4 帧调用栈；错误串只报一次。
2. stdout 在被管道捕获时是块缓冲的，把 stderr 用 `2>&1` 并进同一个流会让未缓冲的 stderr 抢先落流、
   把逐行比对的断言错位（本会话第一轮就是这样红了 1 条）。因此凡断言 stdout 的都用 `2>/dev/null`，
   断言 stderr 的单独取 `2>&1 >/dev/null`，两种流各自再断言退出码。

## 一致性

9 个交付文件 本地 == 真机 的 md5 逐条相等（base64 传输 + 两端 `md5sum` 对拍），全部 LF 行尾、无 BOM：

```
0f353b1582dc3ef4d4c71514957e317c  0.4.0/CMakeLists.txt
b7333b960eac8b008bd9dc5c747e37e1  0.4.0/conandata.yml
b85f9c229bca621706b5f1427174a63a  0.4.0/conanfile.py
3256a32e6ad5b8458b3b1be093a7c6dd  0.4.0/notes.md
3f3e1fee60aad927ce7eccd561330ad8  0.4.0/test_package/MANIFEST.yml
e9d4168048ec6762c47ca43c11bb8044  0.4.0/test_package/conanfile.py
56cca08d438e9be16f69c21ba1525e84  0.4.0/test_package/test_wren_cli.sh
0669f3a02e73718bf6a9bbd44cd4b615  commands.json
33c52bc500ca8d5b4adb70137a1f1dfa  manifest.yaml
```
