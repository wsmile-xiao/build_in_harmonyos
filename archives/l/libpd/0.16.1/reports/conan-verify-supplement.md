# libpd 0.16.1 — `conan-verify` G4/L2/L4/L5 人工补测

- 被补测 SHA：`4711ff450602be20928b8cd6427e051b19f53324`
- 触发原因：`conan-verify` 的 `gate4` 取程序包 ID 时走 `listing["Local Cache"][software][ref]`
  两级索引，而 `conan list <ref>:* --format=json` 的实际结构是
  `{"Local Cache": {"libpd/0.16.1@ohpcd/stable": {...}}}` 单级 → `KeyError`，
  打印 `⚠️ 无法找到程序包 ID` 后直接 `return`（`passed=True`），L2/L4/L5 随之为
  `跳过（无 cache 路径）`，四项仍并列 `✅ PASS`。按 notes/device-facts.md §7.2
  该形态属"整组静默跳过"，须人工补测（脚本不改，属框架层问题）。
- 补测对象（Conan 打包产物）：
  `/storage/Users/currentUser/tmp/libpd-0.16.1/conan-home/p/b/libpdefc8f072f6dc4/p`
- 工具：`/data/service/hnp/bin/{readelf,llvm-nm,clang}`

## G4 产物完整性 ↔ `package_info()`

```
$ find <pkg> -type f | sort
conaninfo.txt
conanmanifest.txt
include/libpd/PdBase.hpp
include/libpd/PdMidiReceiver.hpp
include/libpd/PdReceiver.hpp
include/libpd/PdTypes.hpp
include/libpd/g_canvas.h
include/libpd/m_imp.h
include/libpd/m_pd.h
include/libpd/util/z_print_util.h
include/libpd/util/z_queued.h
include/libpd/z_libpd.h
lib/libpd.so
```

配方 `package_info()`：`libs=["pd"]`、`libdirs=["lib"]`、
`includedirs=["include/libpd","include/libpd/util","include"]`、
`system_libs=["m","pthread","dl"]`（`os in ("Linux","OHOS")`）。

对账：头文件目录与 `includedirs` 一致；`lib/libpd.so` 与 `libs=["pd"]`（`-lpd`）一致；
包内无 `bin/`，与「纯库包、不需要 `commands.json`」一致（CI L0k 亦未触发）。

导出符号数（`llvm-nm -D --defined-only`）：**1379**，含 `libpd_init`、
`libpd_openfile`、`libpd_process_float`、`libpd_bang`、`libpd_float` 等 `z_libpd.h` 声明的公共 API。

## L2 smoke test（用打包产物真跑消费者）

```
$ clang -I<pkg>/include/libpd -I<pkg>/include/libpd/util libpd_test.c \
      -o libpd_test_packaged -L<pkg>/lib -lpd -lm -lpthread -ldl \
      -Wl,-rpath,<pkg>/lib
$ ./libpd_test_packaged libpdtest.pd .
...
PASS: the [osc~ 440] chain produces audible signal
PASS: the DSP output stays within [-1, 1]
failures=0
$ python3 -c "import ctypes; lib=ctypes.CDLL('<pkg>/lib/libpd.so'); print(lib.libpd_blocksize())"
dlopen OK, libpd_blocksize -> 64
```

L1e 破坏性反向验证（W3 内置）亦确认：移走 `lib/` 与 `include/` 后测试失败
（`[ok] L1e: Negative test confirmed`），说明消费者真实依赖被测产物。

## L4 静态安全扫描

```
$ readelf -h libpd.so | grep -E "Class|Type|Machine"
  Class:   ELF64
  Type:    DYN (Shared object file)
  Machine: AArch64

$ readelf -lW libpd.so | grep -E "GNU_STACK|GNU_RELRO"
  GNU_RELRO  0x0eda10 0x00000000000efa10 ... R   0x1
  GNU_STACK  0x000000 0x0000000000000000 ... RW  0     # NX：无可执行位

$ readelf -dW libpd.so | grep -E "SONAME|NEEDED|BIND_NOW|FLAGS|TEXTREL|RPATH|RUNPATH"
  (NEEDED)  Shared library: [libc.so]
  (SONAME)  Library soname: [libpd.so]
  (FLAGS)   SYMBOLIC BIND_NOW
  (FLAGS_1) Flags: NOW
```

判定：NX + RELRO + BIND_NOW 全在；无 `TEXTREL`、无 `RPATH`/`RUNPATH`（消费者由 Conan
RPATH 管理）；`SONAME` 为相对名。

## L5 产物基线与可复现性

同一份源码、同一配方、两个**独立构建树**（`conan-verify` 的 G2 与 `finish` 的 W3）
各产出一份 `lib/libpd.so`：

```
$ sha256sum <pkgA>/lib/libpd.so <pkgB>/lib/libpd.so
0ca6c9912eed4cbae80a202445cf0326f05883289450095bcdf41bdf723288f1  <pkgA>/lib/libpd.so
0ca6c9912eed4cbae80a202445cf0326f05883289450095bcdf41bdf723288f1  <pkgB>/lib/libpd.so
$ strings <pkgA>/lib/libpd.so | grep -c "conan-home\|/p/b/\|libpd-explore"
0
```

结论：产物**跨构建树逐字节一致**（聚合 sha256 稳定），且未把构建期路径编入二进制
（不存在 libvpl 那类"前缀入 binary"问题）。CI 的 L5 门禁本身也已在本轮通过：
`L5_RESULT=pass: lib/ has content`，且 W3 日志中无任何 `[fail]` 行。

## 首轮 L5a 失败与修复

首轮（SHA `f94c6239b3`）W3 报：

```
[fail] L5a: libpd.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址
[fail] L5: SONAME quality gate failed (1 errors)
```

根因：上游 Makefile 的链接行只有 `-shared -Wl,-Bsymbolic`，不传 `-soname`。
修复：配方 `ADDITIONAL_LDFLAGS` 追加 `-Wl,-soname,libpd.so`（与安装出的未版本化文件名一致），
不改上游源文件。复验后 `L5_RESULT=pass`，W3 全绿。
