# sbagen 1.4.5 适配笔记（OpenHarmony PC / aarch64）

## 编译环境

| 项 | 值 |
|----|----|
| 构建系统 | 上游无标准构建系统（仅 `mk*` 脚本）→ 配方内自定义调用编译器 |
| 编译器 | OHOS SDK clang 15.0.4（Target `aarch64-unknown-linux-ohos`），来自 Conan profile（R33） |
| 平台 profile | `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / clang 15） |
| 编译命令 | `clang -DT_POSIX -D_GNU_SOURCE -Wall -O2 sbagen.c -o sbagen -lm -lpthread` |
| 状态 | built（W3 本地 CI 模拟 exit_code=0，Pass rate 100.0%；conan-verify G0–G4 通过；L2/L4/L5 由 W3 覆盖：L2=skip（sbagen 无 `--version`/`--help` 长选项）、L4=pass、L5=pass） |
| 日期 | 2026-10-01 |

源码：上游官方 `https://uazu.net/sbagen/sbagen-1.4.5.tgz`，713168 字节，
sha256 `02b05d0f89f1baa6e6b282f4a5db279b4c59ee6fc400a5a9686aa11287f220e4`
（与 FreeBSD ports / FreshPorts 记录逐字节一致）。

## 项目形态判断（为什么不是 autotools/cmake 模板）

上游 `sbagen-1.4.5` 是**单文件 C 项目**（`sbagen.c`，3247 行）：发布包内既没有
`configure`，也没有 `Makefile`，只有一组 `mk` 构建脚本：

| 脚本 | 内容 | 是否可用于 OHOS |
|------|------|----------------|
| `mk` / `mk-ansi` | `cc -DT_LINUX ...`（OSS_AUDIO，需 `/dev/dsp`） | ❌ OHOS 无 OSS 设备 |
| `mk-nodevdsp` | `cc -DT_POSIX ...`（无 `/dev/dsp`，文件/管道输出） | ✅ **本配方采用** |
| `mk-debug` / `mk-blackfin` | 调试/BF533 DSP 目标 | ❌ 平台无关或非目标平台 |
| `mk-libmad-linux` | 追加 libmad（MP3 解码） | ❌ libmad 属可选解码器，tremor 未发布 |

另外这些脚本的 shebang 指向 `/bin/bash`（OHOS 无该路径），且默认带 `-m32`
（32 位）。因此配方**不执行 mk 脚本**，直接在 `build()` 内按 `mk-nodevdsp` 的
口径调用编译器。

平台宏语义（源码头部）：

```
T_POSIX  = NO_AUDIO + UNIX_TIME + UNIX_MISC   ← 任意 POSIX 平台，文件/管道输出
T_LINUX  = OSS_AUDIO + UNIX_TIME + UNIX_MISC + ANSI_TTY  ← 需要 /dev/dsp
```

## 编译验证过程（探索阶段实测）

在 OHOS 目标机上以三种口径各编译一次，均 RC=0：

| 变体 | 命令 | 结果 |
|------|------|------|
| A | `clang -DT_POSIX -Wall -O3 -s -lm sbagen.c` | RC=0，产物 63872 B |
| B | `clang -DT_LINUX -Wall -O3 -s -lm sbagen.c -lpthread` | RC=0 |
| C | `clang -DT_POSIX -Wall -O3 -s -lm sbagen.c -lpthread` | RC=0 |

`T_LINUX` 变体虽然能编译，但没有 OSS 音频设备可用；**选定 A/C 同族的
`T_POSIX`（NO_AUDIO）路径**，并在配方中保留 `-lpthread`（`UNIX_MISC` 会用到
pthread 相关代码）。

冒烟与功能实测（工作目录 $TMPDIR 下）：

```bash
# 无音频设备时的默认行为（明确提示，而非崩溃）
$ bin/sbagen -Q -i -L 00:00:01 "200+10/20"
Direct output to soundcard not supported on this platform.
Use -o or -O to write raw data, or -Wo or -WO to write a WAV file.   # → stderr, rc=1

# 文件/管道输出：尺寸严格等于 秒数 × 44100 × 2ch × 2B
$ bin/sbagen -Q -i -o out.raw -L 00:00:02 "200+10/20"    # 352800 B
$ bin/sbagen -Q -W -i -o out.wav -L 00:00:02 "200+10/20" # 352844 B（+44 头）
$ bin/sbagen -Q -i -O -L 00:00:01 "200+10/20"            # stdout 176400 B

# 混音（-m）真实生效：与非混音长度相同但内容不同（sha256 不同）
# 确定性：同参数两次运行 sha256 完全一致
# 上游示例序列：-S -q 1 -o seq.raw -L 00:00:03 examples/.../wave-01.sbg  # 529200 B

# 未编译的可选解码器：优雅报错
$ bin/sbagen -Q -i -m x.ogg -o o.raw -L 00:00:01 "200+10/20"
Sorry: Ogg support wasn't compiled into this executable          # → stderr, rc=1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `mk` 脚本无法执行 | shebang `/bin/bash`，OHOS 无该路径；且默认 `-m32` | 不执行 mk 脚本，按 `mk-nodevdsp` 口径直接调用 clang |
| 2 | 有音频设备假设不成立 | OHOS 无 OSS 音频设备（无 `/dev/dsp`） | 采用上游自带 `T_POSIX`（NO_AUDIO）目标，输出走文件/管道（零补丁） |
| 3 | 编译时 `unable to make temporary file` | OHOS 目标机 `/tmp` 只读（E002） | 配方 `build()` 与 test_package 均显式注入可写 `TMPDIR` |
| 4 | 可能打包错架构二进制 | 上游 tarball 内自带 32 位 x86 预编译 `sbagen` 与 `libs/*.a` | `package()` 只收 `build_folder` 里的自建产物；test_package 增加 `ELF machine=aarch64` 断言 |
| 5 | 一次冒烟写出 608MB | `-p` 预编程序列**无视 `-L`**，整段序列直接落盘 | 测试与冒烟避开 `-p`，一律用 `-i` + `-L` 控制时长 |
| 6 | 可选解码器不可用 | OGG/MP3 需要 tremor/libmad，tremor 未在 OHOS 制品仓发布（R36） | 保持关闭，作为已知能力缺口记录；运行时明确提示而非崩溃 |

## 源码修改

**无补丁**（`patches/` 为空）。平台适配完全依赖上游内置的 `T_POSIX` 目标宏，
未对源码做任何改动，也未使用平台宏守卫（R8 无涉）。

## 依赖版本

无三方依赖（0 个 `requires`）：`sbagen.c` 只用 libc/libm/libpthread。
可选解码库 libmad（制品仓已发布）与 tremor（未发布）均**不启用**。

## 上游测试情况（R51 三步法）

1. **清点**：上游发布包内无 `configure`/`Makefile`，不存在 `make check`；无
   ctest/pytest/meson 等测试框架注册项。`scripts/` 下有 7 个脚本（打包日志实测 `Packaged 7 '.sh' files`）
   （`t-seqall.sh`、`t-focus.sh`、`t-focus-1.sh`、`t-focus-2.sh`、`t-focus2.sh`、
   `t-wave-1.sh`、`t-wave-2.sh`），但它们是**交互式演示脚本**：开篇 `cat` 使用
   说明 → `read xx` 等待用户回车 → 以 `-i` 实时播放音调 → 依赖 `^C` 结束，
   既无断言也无退出码语义。
2. **实际运行**：在 OHOS 目标机上以非交互方式复现了这些脚本的核心行为
   （同样的 tone-set/序列文件经 `-S -q 1 -o <file> -L` 合成到文件），逐项验证
   输出尺寸与内容；交互式实时播放段落因无音频设备无法运行（`T_POSIX`
   明确提示 `Direct output to soundcard not supported on this platform`）。
3. **如实申报**：上游无自动化测试可运行（清点证据见上），因此本包自带两层
   真实消费者测试（见下），断言总数 **44**（C 侧 12 + Python e2e 32）。
   实测证据：同一次 `conan create` 的标准输出中出现
   `[test_cli_consumer] 12/12 checks passed` 与
   `[sbagen_consumer_e2e] 32/32 checks passed`（`reports/` 不随 PR 提交，
   故以 test_package 内可复现的 `conan create archives/s/sbagen/1.4.5` 为准）。

## 验证结果

```bash
# 1) 配方门禁（conan-verify）：G0-G4 通过（L2/L4/L5 在本地由 W3 覆盖）
ohc-run.py conan-verify sbagen 1.4.5     # → ✅ 配方验证通过，可标记 published

# 2) W3 本地 CI 模拟（与 CI 同源脚本）
ohc-run.py finish sbagen 1.4.5 built
#   → L1_RESULT=pass / L2_RESULT=skip（无 --version/--help 长选项）
#     L4_RESULT=pass / L5_RESULT=pass，Pass rate 100.0% (1/1)
#   → L1e 破坏性负测 ok：移走 bin/ 后测试确败 → 证明测试真实依赖被测包（R34）
#   → .ci-result.json: exit_code=0；其中 integrity_hash / log_sha256 由每次 finish
#     按时间戳与日志重算（sha256(f"{timestamp}:{software}:{version}:{exit_code}")[:16]），
#     权威读数以该文件实物为准，本文档不写死其值

# 3) 消费者测试（test_package，44 项断言）
conan test ... sbagen/1.4.5@ohpcd/stable  # C 侧 12/12 + e2e 32/32
```

消费者测试两层：

| 层 | 文件 | 内容 |
|----|------|------|
| C 消费者 | `test_package/test_cli_consumer.c` | fork+execv 调用 `bin/sbagen` 合成 2s WAV，解析 RIFF/WAVE 头（2ch/44100Hz/16bit/data 长度），校验左右声道非静音且互异（双耳拍频），并检查 `-h` 版本号 |
| CLI e2e | `test_package/sbagen_consumer_e2e.py` | 产物契约 + ELF aarch64 架构断言 + `-h` + 合成确定性 + raw/WAV 尺寸口径 + 混音生效 + `-O` 管道输出 + 上游示例序列合成 + 无设备提示 + 未编译解码器优雅报错 + 未知选项 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/sbagen` | ~63 KB | 命令行工具本体（aarch64 自建产物） |
| `share/doc/sbagen/*.txt` | — | 上游手册（SBAGEN.txt）、README、ChangeLog、theory/wave/focus 等文档 |
| `share/sbagen/examples/**/*.sbg` | — | 上游示例序列（basics/contrib/focus 等） |
| `share/sbagen/scripts/*` | — | 上游预编程序列与演示脚本 |
| `commands.json` | 404 B | 软件级 CLI 声明（R38，type=tool） |

## 注意事项

- 运行时**必须**提供可写 `TMPDIR`（OHOS `/tmp` 只读，E002），写 WAV/raw 到文件时
  路径需可写。
- 无音频设备时（OHOS 常态）只能输出到文件/管道：`-o`/`-O`（raw）、`-W`/`-WO`（WAV）。
- `.ogg`/`.mp3` 混音输入不受支持（可选解码器未编译），程序会给明确提示。
- `-p <预编程序列名>` 会**忽略 `-L`** 写出整段序列（可能数百 MB），批量/自动化
  场景请用 `-i <tone-spec>` 配合 `-L`。
---

**编译结束**: 2026-10-01 14:48
**最终状态**: built
