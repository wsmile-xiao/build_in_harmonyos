# conan-verify 跳过项人工补测 — radamsa 0.7（package_type=application）

依据：`package_type="application"` 的纯可执行包在 conan-verify 的
G4/L2/L4/L5 走「无 cache 路径/跳过」分支但并列打印 `✅ PASS`（已知形态）。
本文件对四个跳过面逐项人工补测；包定位用 `conan cache path`（非 ls 前缀猜测）。

- 安装树：`/storage/Users/currentUser/.conan2/p/b/radamc52cf2ad9aaf3/p`
  （来源：`reports/conan-create.log` 的 `Package folder` 行；两轮独立干净轮的
  安装产物 sha256 逐字节一致）
- 构建树（source folder）：`/storage/Users/currentUser/.conan2/p/radam75473eb454fbc/s`
- readelf：`/data/service/hnp/bin/llvm-readelf`（绝对路径）

## G4 补测：产物清单 ↔ package_info()

`find <安装树> -type f | sort`：

```text
/storage/Users/currentUser/.conan2/p/b/radamc52cf2ad9aaf3/p/bin/radamsa
/storage/Users/currentUser/.conan2/p/b/radamc52cf2ad9aaf3/p/conaninfo.txt
/storage/Users/currentUser/.conan2/p/b/radamc52cf2ad9aaf3/p/conanmanifest.txt
/storage/Users/currentUser/.conan2/p/b/radamc52cf2ad9aaf3/p/licenses/LICENCE
/storage/Users/currentUser/.conan2/p/b/radamc52cf2ad9aaf3/p/share/man/man1/radamsa.1
```

与 `package_info()` 声明一致：`bindirs=["bin"]`、`libdirs=[]`、
`includedirs=[]`、`libs=[]`（单文件 CLI，无头文件、无库产物）；
`package()` 交付 bin/radamsa + share/man/man1/radamsa.1 + licenses/LICENCE 三件，
与安装树一致（conaninfo/conanmanifest 为 conan 自身元数据，非包内容）。

## L2 补测：真跑消费者

`conan create` 的 test_package 段（`reports/conan-create.log:154-162`）真跑
安装产物 8 项断言全部 `ok`（4 项上游功能复验 + 4 项鸿蒙特有，含
`stdout>/dev/null` 字符设备 poll 回归），`assertions_run=8`。安装二进制
`--version` 输出 `Radamsa 0.7`（conan-create.log:114）。

## L4 补测：静态安全形态（llvm-readelf）

命令与读数（`<B>` = 安装树 bin/radamsa）：

```text
$ llvm-readelf -h $B | grep -E "Type|Machine"
  Type:                              DYN (Shared object file)
  Machine:                           AArch64
$ llvm-readelf -lW $B | grep -E "GNU_STACK|GNU_RELRO"
  GNU_RELRO      0x0459d0 0x00000000000479d0 0x00000000000479d0 0x000430 0x000630 R   0x1
  GNU_STACK      0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0x0
$ llvm-readelf -dW $B | grep -E "BIND_NOW|FLAGS|NEEDED|RUNPATH"
  0x0000000000000001 (NEEDED)       Shared library: [libc.so]
  0x000000000000001e (FLAGS)        BIND_NOW
  0x000000006ffffffb (FLAGS_1)      NOW PIE
```

判读：DYN（PIE）✓；GNU_STACK 为 RW（无可执行位 → NX 生效）✓；
GNU_RELRO 存在 + BIND_NOW（FULL RELRO 形态）✓；唯一 NEEDED=libc.so，
零第三方依赖 ✓（与「Zero deps」预期一致，无需 RUNPATH）。

## L5 补测：产物基线（稳定聚合 sha256，2026-09-22 干净轮安装树）

```text
ee70f744cf5fe25ea4b9a5a896a5697cdde2cf39b83a75fc3702d9e5f178645b  bin/radamsa
f0fcf64cb28ffc5f1fc64c9a1e71279e1a368a9ce149a6dae9819c91632ae1b7  share/man/man1/radamsa.1
4f31f940cb888ab4f6519774ee220f8c1b27871f8d278812b2572185e0013d96  licenses/LICENCE
```

补充：构建中间生成物 radamsa.c 具有字节级确定性——两次独立构建
sha256 均为 `2d70a4ce2606a4801d1b0842449191d0fe361ca006caeb04f3e0ce22a4014095`，
这同时证明 patches/0001 对生成物的套用是确定性的（补丁 hunks 固定）。

## 附：OHOS 字符设备 poll 缺陷对照（patches/0001 的必要性证据）

未打补丁（上游原版构建）与打补丁二进制在同一命令下的对照
（命令 = 上游 tests/1k.sh 同型：`echo 'x' | radamsa --seed 42 -M tmp/meta -n 1000 -o - > /dev/null`）：

```text
未打补丁 bin/radamsa（上游原版构建）:   挂起 >45s 无返回（python 子进程超时强制终止）
已打补丁 bin/radamsa-v2（0001 do_poll S_ISCHR）: 完成 rc=0 用时 2.9s
```

平台探针读数（一手 C 探针，全部有限超时避免探针自身挂死）：

```text
wnull  poll100 /dev/null POLLOUT: r=0 revents=0 errno=0     ← 永不报告可写
wzero  poll100 /dev/zero POLLOUT: r=0 revents=0 errno=0     ← 永不报告可写
rnull  poll100 /dev/null POLLIN : r=1 revents=1 errno=0     ← 读就绪正常
rfile  poll100 regular  POLLIN : r=1 revents=1 errno=0      ← 普通文件正常
wfile  poll100 regular  POLLOUT: r=1 revents=4 errno=0      ← 普通文件正常
V3/V4  poll POLLOUT fd1(管道)  : r=1 revents=4（零超时/100ms 均立即就绪）
D/E    select/poll 无限超时 管道写端: r=1 立即返回        ← 管道无限等待正常
A/B    select/poll 无限超时 fd1=/dev/null: >8s 不返回      ← 挂死形态
```

即：缺陷面恰好是「字符设备写就绪」，Owl Lisp VM 写 stdout 前以无限超时
poll 写就绪（`do_poll` → `select(nfds, ..., NULL)`，radamsa.c:7115），因此
`radamsa ... > /dev/null` 永久挂起。补丁在 `do_poll` 写集加 `fstat` 预检：
S_ISCHR 的 fd 直接判可写立即返回；管道/套接字/普通文件保持原生 select 路径。
