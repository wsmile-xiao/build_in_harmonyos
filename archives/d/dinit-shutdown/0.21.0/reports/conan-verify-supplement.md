# conan-verify 补充验证 — dinit-shutdown 0.21.0（纯可执行包跳过路径人工补测 + 鸿蒙平台契约）

依据：`reports/conan-verify-report.md` 中 G4/L2/L4/L5 在打印 `✅ PASS` 的同时带 `⏭️ 跳过（无 cache 路径）`（工具缺陷：`g.passed` 初值 True + 包定位失败被吞）。按流程第 7.2 节，`package_type = "application"` 的纯可执行包必须人工补测下列四项，本文件为实测记录。

- 被验证提交：`818f8c24fe40e09ee8724f0cbd43d725a9a6b5f0`（清缓存后的干净构建轮）
- 包目录定位（缓存分片名每轮重建，故用 glob 而不写死）：`${CONAN_HOME:-$HOME/.conan2}/p/*/dinit*/p`
- 缓存 ref：`dinit-shutdown/0.21.0@ohpcd/stable`
- 采集时间：2026-09-11 19:25:25

## G4 产物清单 × package_info() 互证

```console
$ find . -type f | sed 's|^\./||' | sort     # 在 glob 定位到的包目录内
bin/dinit-halt
bin/dinit-poweroff
bin/dinit-reboot
bin/dinit-shutdown
bin/dinit-soft-reboot
conaninfo.txt
conanmanifest.txt
licenses/LICENSE
```

配方声明 `package_type = "application"`、`package_info()` 设 `bindirs=["bin"]`、`libdirs=[]`、`includedirs=[]`。实测包内只有 `bin/`（5 个可执行文件）与 `licenses/`，无 `lib/`、无 `include/`，与声明一致。

## L2 消费者实测（真实命令行为）

```console
$ <包目录>/bin/dinit-shutdown --help
dinit-shutdown :   shutdown the system
rc=1

$ <包目录>/bin/dinit-halt --help
dinit-halt :   shutdown the system
rc=1

$ <包目录>/bin/dinit-poweroff --help
dinit-poweroff :   shutdown the system
rc=1

$ <包目录>/bin/dinit-reboot --help
dinit-reboot :   shutdown the system
rc=1

$ <包目录>/bin/dinit-soft-reboot --help
dinit-soft-reboot :   shutdown the system
rc=1

$ <包目录>/bin/dinit-shutdown -Z
Unrecognized command-line parameter: -Z
rc=1

$ <包目录>/bin/dinit-shutdown    # 无守护进程：仅 connect，不会触发 reboot(2)
connect: No such file or directory
rc=1
```

另有独立的消费者测试程序 `test_package/test_dinit_shutdown.py`（`conan create` 的 test_package 阶段实跑）：`RESULT: 48 checks, 48 passed, 0 failed` —— 39 条 CLI 行为断言 + **9 条鸿蒙平台契约断言**，完整输出见 `reports/cli-behaviour.txt`。

## 鸿蒙平台契约（鸿蒙特有测试，9 条断言）

由 `test_package/test_dinit_shutdown.py` 的 `ohos_platform_contract()` 直接读交付产物字节/ELF 头断言；全部通过（`conan create` 日志节选）：

```text
  ok   OHOS: artifact is a 64-bit little-endian ELF
  ok   OHOS: artifact targets AArch64 (e_machine=183, expected 183)
  ok   OHOS: artifact is position independent (e_type=3, expected ET_DYN)
  ok   OHOS: .codesign section kept (hnp toolchain signature; re-signing or stripping breaks loading on this platform)
  ok   OHOS: symbol table kept, binary not stripped (stripped builds exit 126 here)
  ok   OHOS: compiled-in control socket literal /var/run/dinitctl\0 present (upstream non-Linux default)
  ok   OHOS: compiled-in command prefix literal 'dinit-reboot'NUL present (--shutdown-prefix)
  ok   OHOS: compiled-in command prefix literal 'dinit-soft-reboot'NUL present (--shutdown-prefix)
  ok   OHOS: all 4 alias executables are byte-identical to bin/dinit-shutdown
```

判据来源（设备实测对照，同一次采样）：

- 第 5 条（未 strip）：未 strip 的产物 `.symtab`/`.codesign` 计数均为 1 且可运行（`--help` 退出码 1 = usage）；用 `strip` 处理后两者计数归零，且**本平台加载失败、退出码 126**（shell 报 `Permission denied`，Python 侧 `PermissionError [Errno 13]`）。
- 第 6–8 条（NUL 结尾字面量锚定）：等长反例构造 —— 把 socket 字面量后的 NUL 改成 `X`（长度不变）后，裸子串断言 `b"/var/run/dinitctl"` 仍为 True（误放行），而 NUL 锚定断言为 False（正确拒绝）；该反例的完整输出见 `reports/cli-behaviour.txt` 的「OHOS 平台契约」节。
- 第 9 条（别名一致性）：4 个别名与 `bin/dinit-shutdown` 逐字节一致（本包按普通文件交付别名，此断言守住 `package()` 的复制步骤）。

## L4 静态安全属性（逐个 bin/ 可执行文件）

```console
$ readelf -h/-lW/-dW dinit-halt
    Type:                              DYN (Position-Independent Executable file)
    Machine:                           AArch64
    GNU_RELRO      0x008a70 0x000000000000aa70 0x000000000000aa70 0x000688 0x001590 R   0x1
    GNU_STACK      0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0
   0x000000000000001e (FLAGS)              BIND_NOW
   0x000000006ffffffb (FLAGS_1)            Flags: NOW PIE
   0x0000000000000001 (NEEDED)             Shared library: [libc++_shared.so]
   0x0000000000000001 (NEEDED)             Shared library: [libc.so]
  .codesign 节数=1

$ readelf -h/-lW/-dW dinit-poweroff
    Type:                              DYN (Position-Independent Executable file)
    Machine:                           AArch64
    GNU_RELRO      0x008a70 0x000000000000aa70 0x000000000000aa70 0x000688 0x001590 R   0x1
    GNU_STACK      0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0
   0x000000000000001e (FLAGS)              BIND_NOW
   0x000000006ffffffb (FLAGS_1)            Flags: NOW PIE
   0x0000000000000001 (NEEDED)             Shared library: [libc++_shared.so]
   0x0000000000000001 (NEEDED)             Shared library: [libc.so]
  .codesign 节数=1

$ readelf -h/-lW/-dW dinit-reboot
    Type:                              DYN (Position-Independent Executable file)
    Machine:                           AArch64
    GNU_RELRO      0x008a70 0x000000000000aa70 0x000000000000aa70 0x000688 0x001590 R   0x1
    GNU_STACK      0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0
   0x000000000000001e (FLAGS)              BIND_NOW
   0x000000006ffffffb (FLAGS_1)            Flags: NOW PIE
   0x0000000000000001 (NEEDED)             Shared library: [libc++_shared.so]
   0x0000000000000001 (NEEDED)             Shared library: [libc.so]
  .codesign 节数=1

$ readelf -h/-lW/-dW dinit-shutdown
    Type:                              DYN (Position-Independent Executable file)
    Machine:                           AArch64
    GNU_RELRO      0x008a70 0x000000000000aa70 0x000000000000aa70 0x000688 0x001590 R   0x1
    GNU_STACK      0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0
   0x000000000000001e (FLAGS)              BIND_NOW
   0x000000006ffffffb (FLAGS_1)            Flags: NOW PIE
   0x0000000000000001 (NEEDED)             Shared library: [libc++_shared.so]
   0x0000000000000001 (NEEDED)             Shared library: [libc.so]
  .codesign 节数=1

$ readelf -h/-lW/-dW dinit-soft-reboot
    Type:                              DYN (Position-Independent Executable file)
    Machine:                           AArch64
    GNU_RELRO      0x008a70 0x000000000000aa70 0x000000000000aa70 0x000688 0x001590 R   0x1
    GNU_STACK      0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0
   0x000000000000001e (FLAGS)              BIND_NOW
   0x000000006ffffffb (FLAGS_1)            Flags: NOW PIE
   0x0000000000000001 (NEEDED)             Shared library: [libc++_shared.so]
   0x0000000000000001 (NEEDED)             Shared library: [libc.so]
  .codesign 节数=1

```

判据：`Type: DYN (Position-Independent Executable file)` + `GNU_STACK ... RW`（NX）+ `GNU_RELRO` + `FLAGS BIND_NOW` + `FLAGS_1 ... PIE`，5 个产物全部满足。产物未 strip（保留 `.codesign` 段），也未执行 `binary-sign-tool sign -selfSign` 重签。

## L5 产物基线与可复现性

可复现性判别：同一提交上多次**清缓存后从源码重建**（缓存分片名每轮重建，如 `dinit4755628b6ed0f`、`dinite98c7d3fb4ef9`、`dinit5c10e7f45d2c2`、`dinit9037840eb29cd`、`dinit6482f03a99cc4` 及本轮分片），逐产物 sha256 各轮完全一致，无 `__DATE__`/`__TIME__` 或构建目录路径漂移。

```console
$ cd <glob 定位到的包目录>
$ find . -type f ! -name conaninfo.txt ! -name conanmanifest.txt | sed 's|^\./||' | sort | xargs sha256sum
f3a81ed0a436e743b4ff6a1d0507a569ab7a70dc228476d16e4a28e50a119200  bin/dinit-halt
f3a81ed0a436e743b4ff6a1d0507a569ab7a70dc228476d16e4a28e50a119200  bin/dinit-poweroff
f3a81ed0a436e743b4ff6a1d0507a569ab7a70dc228476d16e4a28e50a119200  bin/dinit-reboot
f3a81ed0a436e743b4ff6a1d0507a569ab7a70dc228476d16e4a28e50a119200  bin/dinit-shutdown
f3a81ed0a436e743b4ff6a1d0507a569ab7a70dc228476d16e4a28e50a119200  bin/dinit-soft-reboot
cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30  licenses/LICENSE

$ # 包内容聚合（相对路径；conanmanifest.txt 首行为打包时间戳，故排除 conaninfo/conanmanifest）
$ find . -type f ! -name conaninfo.txt ! -name conanmanifest.txt | sed 's|^\./||' | sort | xargs sha256sum | sha256sum
d7c8b9ed5ad459422b361d2ccf9fb7e7fe530d528fb8a10ba13e858f971d7409  -
```

基线结论：5 个可执行文件内容相同（`f3a81ed0a436e743b4ff6a1d0507a569ab7a70dc228476d16e4a28e50a119200`，即同一二进制按 `basename(argv[0])` 分派），跨多轮干净构建可复现；包内容聚合 `d7c8b9ed5ad459422b361d2ccf9fb7e7fe530d528fb8a10ba13e858f971d7409` 为稳定基线。

## 上游用例计数在 create 日志中的对账

`reports/conan-create.log` 内上游用例行（`用例名... PASSED` 形态）计 **136** 条，另有 1 行 `PASSED 48/48` 是消费者测试程序自己的汇总行。上游口径的取数命令（与 `test_package/MANIFEST.yml` 声明一致）为 `make -C src check 2>&1 | grep -c 'PASSED'` = 136。
