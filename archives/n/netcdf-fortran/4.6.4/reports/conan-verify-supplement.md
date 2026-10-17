# conan-verify 人工补测报告 — netcdf-fortran 4.6.4

**补测原因**：`conan-verify` 报告里 G4/L2/L4/L5 四组均写 `✅ PASS`，但其下一行是
`⏭️ 跳过（无 cache 路径）`——按工作流第 7.2 节，**以跳过为准**，`✅` 是工具文案缺陷。
跳过根因是 `conan_verify.py` 的 G4 定位用 `conan list --format=json` 顶层键（带
`@user/channel`）去匹配 `self.ref`（不带），`KeyError` 被吞后整组走「无 cache 路径」分支。
故本节按第 7.2 节列出的判据**人工补测**四组。

**对象 SHA**：见 PR 正文的最终 SHA（本报告随该 SHA 一同提交）
**采信轮**：clean-cache `conan-verify`（`rc=0`，G1/G0/G2/G3 PASS）
**采信轮包目录**：`~/.conan2/p/b/netcdc8cd9652c8fba/p`（glob 定位：
`ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/netcd*/p`）

> 关联证据：`reports/conan-create.log`（采信轮干净轮日志：`Calling build()` 存在、
> `100% tests passed, 0 tests failed out of 51`、test_package `27/27`）。

---

## G4：产物完整性（声明 vs 实际）

判据：包目录实际文件清单与 `package_info()` 声明互相印证。

`package_info()` 声明：`libs=["netcdff"]`、`includedirs=["include"]`、`bindirs=[]`、
`requires=["netcdf::netcdf"]`。

实际包内容（`find <pkg> -type f -o -type l`，26 项）：

| 路径 | 印证 |
|---|---|
| `lib/libnetcdff.so` → `libnetcdff.so.7` → `libnetcdff.so.7.1.0` | `libs=["netcdff"]` ✓，版本软链完整 |
| `include/*.mod` × 11、`include/netcdf.inc` | `includedirs=["include"]` ✓ |
| `bin/nf-config` | 配置脚本；`bindirs=[]` 与其非 CLI 工具定位一致 ✓ |
| `lib/cmake/netCDF-Fortran/*`、`lib/pkgconfig/netcdf-fortran.pc` | 消费方发现入口 ✓ |
| `lib/objects-Release/netcdff_c/*.o` | 上游有意安装的 OBJECT 库 ✓ |
| `licenses/COPYRIGHT`、`share/man/man3/netcdf_fortran.3` | 许可与手册 ✓ |

结论：**声明的 `libs`/`includedirs` 与真实产出一致；`bindirs=[]` 与 `bin/` 仅含配置脚本一致**。

---

## L2：平台功能矩阵（真实消费者行为）

判据：对**包产物**跑真实消费者，取得业务输出而非仅退出码。

做法：在仓库外新建消费者工程，`conan install --requires="netcdf-fortran/4.6.4@ohpcd/stable"`
取包（`-g CMakeDeps -g CMakeToolchain`），用 `find_package(netCDF-Fortran)` 编译
`test_package/test_netcdf_fortran.f90`，再以 `conanrun` 环境直跑：

```
L2 run_rc=0
RESULT: netcdf-fortran consumer checks 27/27 passed
PASS: netcdf-fortran 消费者链路全通过
```

消费者覆盖：建 netCDF-4 文件 → 定义 2 维/1 变量 → 写属性 → 开 HDF5 deflate →
写 12 个 double → 关闭 → 只读重开 → 校验格式/维度数/变量数/变量名/类型/属性/维度名与长度/
属性值/数据逐元素一致。

第二个消费者 `test_netcdf_fortran_abi.c`（C 侧交付面契约）同样由 test_package 真实执行：

```
  [ok]   dlopen("libnetcdff.so.7", RTLD_NOW) 全部重定位可解析
  [ok]   dlsym "_QMnetcdfPnf90_create" / "_QMnetcdfPnf90_open" / ... / "_FortranATrim" ...
  [ok]   实际加载: <pkg>/lib/libnetcdff.so.7
RESULT: netcdf-fortran ABI contract checks 10/10 passed
```

结论：**L2 通过（消费者合计 37/37：Fortran 数据链路 27 + C 侧加载/ABI 契约 10），
两个消费者都是库产物的真实使用者**。

---

## L4：安全属性

### 库产物 `lib/libnetcdff.so.7.1.0`

| 判据 | 实测 |
|---|---|
| `DYN` | `Type: DYN (Shared object file)` ✓ |
| `GNU_STACK RW` | `GNU_STACK ... RW` ✓ |
| `GNU_RELRO` | 存在 ✓ |
| `FLAGS BIND_NOW` | `0x1e (FLAGS) BIND_NOW` ✓ |
| `FLAGS_1 PIE` | 共享库不适用（`FLAGS_1 NOW`）；按工作流本条针对**可执行文件** |

附加核对：`Machine: AArch64`、`SONAME: [libnetcdff.so.7]`、
`NEEDED: libnetcdf.so.22, libc.so`。

### 消费者可执行文件 `test_netcdf_fortran`

| 判据 | 实测 |
|---|---|
| `DYN` | `Type: DYN` ✓ |
| `GNU_STACK RW` | ✓ |
| `GNU_RELRO` | ✓ |
| `FLAGS BIND_NOW` | `0x1e (FLAGS) BIND_NOW` ✓ |
| `FLAGS_1 PIE` | `0x6ffffffb (FLAGS_1) NOW PIE` ✓ |

结论：**L4 通过（库四项 + 消费者五项全备）**。

---

## L5：产物基线与可复现性判别

### 可复现性判别（同提交、两轮 clean-cache 构建）

第 2 轮包目录 `p/b/netcd51015d4368579/p`，第 3 轮 `p/b/netcdc8cd9652c8fba/p`。
逐产物 sha256 比对：26 个文件中 **21 个跨轮逐字节一致**，**5 个不一致**。

| 不一致文件 | 根因 | 是否属预期 |
|---|---|---|
| `conanmanifest.txt` | 首行为打包时间戳 | 预期（工作流已列） |
| `bin/nf-config` | 内嵌 install prefix（含本轮缓存目录名） | 预期（路径型元数据） |
| `lib/pkgconfig/netcdf-fortran.pc` | 同上（`prefix=`/`libdir=`） | 预期 |
| `lib/libnetcdff.settings` | 同上（`Build Directory`/`Install Prefix`） | 预期 |
| `lib/libnetcdff.so.7.1.0` | 见下方节级分析 | 预期（DWARF/路径派生） |

**证据 1 — 路径归一化后文本产物完全一致**：对上述三个文本文件把
`/storage/.../p/b/netcd<name5><hash>` 归一化为 `<CACHE>` 后逐一 `diff`，**全部无差异**。

**证据 2 — `.so` 差异全部是内嵌构建路径，代码节零差异**：

| 节 | 原始字节 | 说明 |
|---|---|---|
| `.text` | 一致 ✓ | 代码本身可复现 |
| `.data` / `.data.rel.ro` / `.dynamic` / `.comment` | 一致 ✓ | |
| `.rodata` | 差异 → **路径归一化后一致 ✓** | 41 条内嵌 `nf_*.F90` 绝对源路径 |
| `.dynstr` / `.dynsym` | 差异 | RUNPATH 字符串 + Flang 的 `_QQclX<路径哈希>` 符号 |

`_QQclX<md5>` 是 Flang 生成的「文件/行检查」符号，其哈希由**源文件路径**派生，
因此随每轮缓存构建目录名变化——属工作流第 7.2 节记载的「DWARF/comp_dir 记录每轮不同
缓存构建目录」同族根因。

**证据 3 — 剔除路径派生符号后导出符号集合完全相同**：

```
llvm-nm -D --defined-only <so> | awk '{print $3}' | grep -v '^_QQclX' | sort
第2轮 2159 个符号 vs 第3轮 2159 个符号 → diff 无输出 ✓
```

### 基线（只对可复现子集给出）

可复现子集 21 个文件的**稳定聚合**（包目录内用相对路径，避免分片目录名每轮重建导致漂移）：

```
cd <pkg> && while read f; do sha256sum "$f"; done < <21 个文件清单> | sha256sum
→ 1dbd844ba5d4e035e3483b448617e4bcae17d036b88556cb71a204b1d6ea888d
```

关键产物逐文件 sha256（第 3 轮采信轮）：

| 文件 | sha256 |
|---|---|
| `include/netcdf.mod` | `007350a6c08c0df822c2b74f68b8bfd9cfc99ebd35b8cd31d40beb419e245d32` |
| `include/typesizes.mod` | `7477634f5e00649e7d9a73e6e8f867e87e54fed9f1189b817a729f6707a240d8` |
| `lib/objects-Release/netcdff_c/nf_lib.c.o` | `f329dc77e833219d549b926bbdfa7f45852dec1ce55dd7df429a009e692e10d9` |
| `lib/objects-Release/netcdff_c/nf_v2compat.c.o` | `85b09392e2619a58286ff28cdfa54a614b9c725d76576fe33a064fb8eed62326` |
| `lib/cmake/netCDF-Fortran/netCDF-FortranConfig.cmake` | `5449b2b9659838435789862ecce06010b93f0dfa2d4fdb274f12f0d6f4203991` |
| `licenses/COPYRIGHT` | `453cdb3cb8b47ceeafdfa29894f2ad2949ec409d3c364b1c1fbdc260484ef000` |

**声明**：`lib/libnetcdff.so.7.1.0` 全文件 sha256 **跨轮不可复现**（第 2 轮
`62f42e7a…`、第 3 轮 `f226258d…`），根因是内嵌的每轮不同缓存构建目录路径
（`.rodata` 源路径 + `.dynstr` RUNPATH 与 `_QQclX*`）；代码节（`.text` 等）与
导出符号集合跨轮完全一致，故不构成构建不可复现。

---

## 未覆盖范围与遗留

- 本补测**不包含** `shared=False` 静态库组合：`options.shared` 已接入
  `BUILD_SHARED_LIBS`（跟随选项），但只实测了默认 `shared=True`。
- 运行期消费者验证依赖 `LD_LIBRARY_PATH` 提供 netcdf-c 传递依赖闭包
  （OHOS loader 不搜索包内绝对路径，`DT_RUNPATH` 会被 `LD_LIBRARY_PATH` 覆盖）。
