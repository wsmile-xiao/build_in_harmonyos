# 被测 CLI 以绝对路径 exec 子进程时，消费者测试必须自带 target 编译的 helper

> 草稿 · 来源 pipexec 2.6.2 适配（feat/pipexec-2.6.2-codex）· 待审核 promote
> 配套 .kv: `knowledge/drafts/DRAFT-pipexec-2.6.2-absolute-path-child-consumer-helper.kv`

## 一句话

有一类 CLI 的**设计语义就是用绝对路径 exec 子进程**（进程编排 / 管道 / 批处理 /
进程监督）。给这类包写 conan `test_package` 时，**必须自带一个为目标平台编译的
子程序（helper）**来充当子进程；沿用 `/bin/echo`、`/bin/cat` 这类系统命令在
HarmonyOS 上必然失败（无传统 `/bin`），而退化成只跑 `--help` 又会被 CI 的
L1e 破坏性反向验证判成假测试。

## 为什么值得单独记

这不是某一个包的怪癖，而是一类包的共性：

| 类别 | 例 | 被测工具对子进程的要求 |
|---|---|---|
| 进程编排 | pipexec | `[ NAME /abs/prog args ]` + `{A:1>B:0}`，内部 `execv(path, …)` |
| 管道计量 | pipemeter / pipebench | 坐在管道中间，需要上游生产者与下游消费者 |
| 批量执行 | xargs / parallel 类 | 每个条目 spawn 一个命令 |
| 进程监督 | supervisor 类 | 拉起并守护子进程 |

它们的**功能只在真的跑起一串子进程时存在**。所以消费者测试必然需要"别的程序"
来协作——而 OHOS 上没有随取随用的 `/bin/*`。

## 现象与根因

三个叠加约束：

1. **路径必须由测试给出**。被测工具不做 PATH 搜索（pipexec 用 `execv` 而非
   `execvp`），子进程路径是测试输入的一部分，且要绝对路径。
2. **HarmonyOS 无传统 `/bin`**（知识库 E165）。设备上 `/bin/sh` 仍在，但
   `/bin/echo`、`/bin/true`、`/bin/cat` 等不在，`/bin` 也不在默认 PATH。
   上游 README / 自有测试里那些 `/bin/...` 例子，直接照搬到测试里就会
   `No such file or directory`。本机 Linux 上却完全正常 → 典型"本地绿、设备红"。
3. **OHOS 上执行新编译的 helper 有额外门槛**：
   - HMDFS 上**脚本**不可 direct-exec（E232）；
   - 新链接的 **ELF 需要 `.codesign` 段**（`binary-sign-tool` 自签名）才能被 exec；
   - 执行位置要落在**可写、非 HMDFS** 的目录（如 `/data/storage/el2/base/cache`），
     否则 Permission denied。

还有一条"走捷径会翻车"的路：把 `test()` 写成只调用被测工具自身的
`--help`/`--version`/无参路径。表面能过，但 CI 有 **L1e 破坏性反向验证**——
它会破坏包产物后重跑你的测试，若测试仍通过就判 `fake test detected (R34)`。

## 推荐做法

### 1. test_package 自带"单二进制多角色" helper

一个 C 源文件，多种模式，覆盖测试要驱动的全部子进程行为。pipexec 实际用的
`pipehelper.c` 提供了：

```
pipehelper produce <n>              产 n 字节确定性数据到 stdout
pipehelper pass                     stdin -> stdout 原样转发
pipehelper consume <path> [expect]  stdin 写入文件，回报字节数（不符则非 0）
pipehelper echo <args...>           参数以单空格连接后输出
pipehelper exit <code>              以指定码退出
pipehelper sleep <seconds>          sleep 后退出
pipehelper abort-once <marker>      首次运行 SIGABRT 自尽，之后退出 0（触发重启语义）
```

要点：**不放任何平台宏**（R8），同一份源码 Linux / OHOS 都能编。

### 2. 用 CMake 为目标平台编译

```cmake
add_executable(pipehelper pipehelper.c)
target_compile_options(pipehelper PRIVATE -Wall -Wextra)
```

`test_package/conanfile.py::build()` 里 `cmake.configure()/build()`。**不要**写
`find_package`/`target_link_libraries`——`application` 包不导出库与 CMake 目标。

### 3. OHOS 上执行前 staging（复制 + 自签名）

```python
if str(self.settings.os) == "OHOS":
    runtime_dir = tempfile.mkdtemp(prefix="pipexec-test-",
                                   dir="/data/storage/el2/base/cache")
    helper = os.path.join(runtime_dir, "pipehelper")
    shutil.copy2(helper_built, helper)
    # binary-sign-tool sign -inFile X -outFile X.signed -selfSign 1
    # 校验 .codesign 段后 os.replace 就位
```

同 `archives/l/libxext/1.3.7`、`archives/p/pipemeter/1.1.5` 的 test_package 范式。

### 4. smoke 脚本参数化绝对路径

```sh
sh smoke.sh <pkg>/bin/pipexec <helper-abs-path> <workdir>
```

脚本内所有子进程一律写成 `"$HELPER"`，断言覆盖**真实数据面**（fd 连线、
字节计量、退出码传播、重启语义）。这样 L1e 破坏包产物后测试必然失败，
证明"测试真的依赖被测包"。

### 5. 上游测试脚本硬编码 `/bin/<tool>` 时

在配方 `build()` 里按 `shutil.which()` 把 `/bin/<tool>` 重定向到本机真实绝对
路径（可加 `/system/bin` 回退），**不改上游断言**（E165 同族做法）。pipexec 的
`test/basic_tests.sh` 就用了 `/bin/true|false|echo|cat|grep`，重映射为
`/system/bin/*` 后 4/4 通过。

## 实证（pipexec 2.6.2）

- 本机（容器，原生工具链）：`smoke.sh` 11/11。
- 真机 shadow CI：`conan create` exit 0；L0/L1/L5 pass；
  `L1e: Negative test confirmed — test genuinely depends on pipexec`；
  上游 `test/basic_tests.sh` 4/4（`/bin/*` 已重映射）；test_package 11/11。
- helper 交叉编译探针：OHOS clang 15 `--target=aarch64-linux-ohos` 零告警，
  产物 `ELF64/AArch64`，`NEEDED` 仅 `libc.so`。

## 与既有条目的关系

- `E165`（HarmonyOS 无 `/bin`）：本条的**成因之一**，本条聚焦"测试侧该如何自备子进程"。
- `E232`（HMDFS 不可 direct-exec 脚本）：解释为何 helper 要 staging 到非 HMDFS 并签名。
- 区别于点名的相邻草稿：`DRAFT-7605`（mkfifo 不可用）、`DRAFT-8960`
  （test_package 里 CLI 读 stdin 需显式 EOF）、`DRAFT-devio-1.2`（消费者测试用 popen
  内存管道替代 /tmp 中间文件）、`DRAFT-8207`（automake 测试脚本 shebang 兜底）——
  它们分别处理"命名管道/stdin/shebang/中间文件"，**均未涉及"被测工具要求绝对路径
  子进程 → 测试须自带目标编译 helper"这一模式**。

## 复用清单（下个同类包怎么做）

1. 判断被测 CLI 是否 `execv`（绝对路径）拉起子进程 —— 看源码 exec 调用与文档
   示例里是否出现 `[ NAME /path ]` / 裸 `/bin/...`。
2. 在 test_package 写一个多模式 helper（`.c` + CMakeLists），不写平台宏。
3. `test()` 里：OHOS → 复制到 `/data/storage/el2/base/cache` + 自签名；
   非 OHOS → 直接用 build 产物。
4. smoke 脚本参数化 `"$HELPER"`，断言覆盖核心数据面（保证能过 L1e）。
5. 上游测试若硬编码 `/bin/*`，`build()` 里按 `which()` 重映射后再跑。
