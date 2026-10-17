# DRAFT-yosys-0.66 — 本机运行 OHOS aarch64 二进制缺 __fd_chk（通道 B）

## 使用说明

想在 x86 主机上**本地执行** OHOS aarch64 产物（通道 B）时，需要 loader 与运行库。
用免 root 的通用 Alpine musl 作 loader 时，OHOS musl 的 fortify 助手 `__fd_chk` 缺失，
程序在重定位阶段直接退出：`Error relocating ...: __fd_chk: symbol not found`。

处置：编一个 aarch64 shim 只定义该符号，用 `QEMU_SET_ENV` 注入（**只作用于 guest**）：

```bash
printf 'void __fd_chk(int fd) { (void)fd; }\n' > /tmp/fdchk.c
$SDK/llvm/bin/aarch64-unknown-linux-ohos-clang --sysroot=$SDK/sysroot \
    -shared -fPIC /tmp/fdchk.c -o $HOME/.ohos/aarch64-musl/lib/libfdchk.so

export LD_LIBRARY_PATH="$SDK/llvm/lib/aarch64-linux-ohos:$SDK/sysroot/usr/lib/aarch64-linux-ohos:$TCL_LIB"
export QEMU_SET_ENV="LD_PRELOAD=$HOME/.ohos/aarch64-musl/lib/libfdchk.so"
./yosys -V
# -> Yosys 0.66 (git sha1 ..., aarch64-unknown-linux-ohos-clang++ 15.0.4 ...)
```

关键点：**不要**直接 `export LD_PRELOAD=...aarch64.so`——宿主的 x86_64 进程（clang/make）会报
`cannot be preloaded: wrong ELF class`。`QEMU_SET_ENV` 由 qemu 解释，只给 guest 设环境。

另外两个常见缺库：`libc++_shared.so`（C++ 项目）与 `libz.so`（tcl 等），都在 SDK 里，
按上面的 `LD_LIBRARY_PATH` 补齐即可。

## 适用范围

- 场景：x86 主机 + `binfmt_misc`/`qemu-aarch64-static` + 通用 musl loader，本地执行 OHOS aarch64 产物
- 症状：重定位阶段 `symbol not found`（fortify `__fd_chk`）或 `Error loading shared library libc++_shared.so / libz.so`
- 不适用：目标架构上原生执行（CI/真机）；或已用 OHOS 官方 musl loader

## 输入输出定义

- 输入：`fdchk.c`（一行）；SDK 的 aarch64 `llvm/lib` 与 `sysroot/usr/lib`；qemu 的 `QEMU_SET_ENV`
- 输出：`libfdchk.so`（aarch64）；guest 进程可正常加载并运行
- 成功信号：二进制打印版本横幅并返回 0

## 示例（含诊断链）

```
$ ./yosys -V
Error relocating /home/.../libtcl8.6.so: __fd_chk: symbol not found
Error relocating /home/.../yosys: __fd_chk: symbol not found          # RC=127

$ grep -rn '__fd_chk' $SDK/sysroot/usr/include/sys/select.h
33:void __fd_chk(int fd);
36:#define FD_SET(d, s) do { __fd_chk(d); ... } while(0)

$ nm -D /home/qianxia/.ohos/aarch64-musl/lib/ld-musl-aarch64.so.1 | grep -c __fd_chk
0                                                                      # 通用 musl 没有
$ nm -D $SDK/sysroot/usr/lib/aarch64-linux-ohos/libc.so | grep __fd_chk
0000000000011d80 T __fd_chk                                            # 但那是链接桩：
$ ls -la $SDK/sysroot/usr/lib/aarch64-linux-ohos/libc.so
-rwxr-xr-x 72144 ... libc.so                                          # 72KB 桩，当 loader 会 segfault

# 注入 shim 后
$ QEMU_SET_ENV="LD_PRELOAD=$HOME/.ohos/aarch64-musl/lib/libfdchk.so" ./yosys -V
Yosys 0.66 (git sha1 86f2ddebce7e98cec..., aarch64-unknown-linux-ohos-clang++ 15.0.4 -fPIC -O3)   # RC=0

# 进一步跑真实综合（含外部 abc）
$ ... yosys -p 'read_verilog test.v; synth -top top; stat'
Time spent: 49% 1x abc (0 sec), ...                                  # RC=0
```

## 查重差异表

| 既有条目 | 相似点 | 本条差异 |
|---|---|---|
| `E999-draft-8FBE`（OHOS libc 符号族 configure 误检的 ac_cv 禁用模式，fortify `__*_chk`） | 都涉及 OHOS fortify `__*_chk` 符号 | 那条是 **configure 阶段误检**（需 ac_cv 禁用）；本条是 **运行期 loader 缺符号**，处置是给 guest 注入 shim（本地验证通道） |
| `DRAFT-lld-shlib-undefined-host-contract` | 都涉及未定义符号 | 那条是 lld 链接期契约；本条是运行期动态加载 |
| **E520**（`draft-review` 预审建议 `merge-into → E520`） | 都属于「运行二进制缺运行库」 | E520 是 **qsb 宿主工具**缺 `LD_LIBRARY_PATH` 里的 Qt 库（缺的是**具体依赖库**，补路径即可）；本条缺的是 **OHOS musl 的 fortify 助手符号 `__fd_chk`**，通用 musl loader 根本没有该符号，补路径无效，必须注入 shim——机制与处置都不同，且本条还包含「用 `QEMU_SET_ENV` 只给 guest 注入、避免污染宿主 x86 进程」这一关键手法。建议 `create`，并在 `similar_to` 互链 |

## 验证证据

```
$ file /home/qianxia/.ohos/aarch64-musl/lib/libfdchk.so
ELF 64-bit LSB shared object, ARM aarch64, ...

$ ./yosys -V
Yosys 0.66 (git sha1 86f2ddebce7e98cec...)                            # RC=0

$ ./test_yosys      # test_package harness，真实执行 -V 与 synth
PASS: yosys -V reports the 0.66 version banner
PASS: synthesized test.v (read_verilog + synth + stat)                # RC=0
```

- 退出码：修复前 127；修复后 0
- 日志绝对路径：`/mnt/e/dsh working/tasks/yosys-0.66-2026-09-17/logs/033-local-create.log`、
  `/mnt/e/dsh working/tasks/yosys-0.66-2026-09-17/logs/041-upstream-vanilla-test.log`
- 上游任务：PR #11115
