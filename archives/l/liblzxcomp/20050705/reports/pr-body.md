## PR 信息
- **三方库名称**：liblzxcomp
- **上游版本**：20050705
- **上游仓库地址**：https://www.russotto.net/chm/lzx.html
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E113（OHOS/HarmonyOS 无 BSD 风格类型 u_char 等）、E392（无 configure 的 raw Makefile Conan 配方模式）、E525（make -j1 强制）、技能 openharmony-compile-agent

> 源码包 URL（conandata.yml）: https://mirrors.ustc.edu.cn/freebsd-ports/distfiles/lzx_compress.tar.gz
> （SHA-256: `d63f046130677db666d6cec6f4a62349060928ec85b1feaf2fce9222293a95f7`）
> 上游作者发布站 russotto.net 已停止服务，源码改用 FreeBSD 官方 distfiles 镜像分发（文件名与
> FreeBSD port 的 DISTNAME 一致：`lzx_compress.tar.gz`，非 fork / 网盘 / 非权威 CDN）。
> 归档路径：`archives/l/liblzxcomp/20050705`

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无单元测试框架（Makefile 无 `check` 目标、无 ctest / meson test） |
| 集成测试 | 1 | 上游自带自测程序 `lzx_test.c`；Makefile 提供 `lzx_test`（slide 变体）与 `lzx_test2`（nonslide 变体，即 `liblzxcomp.a` 的对象集）两个目标，用法为 CLI 整文件压缩验证 |
| 其他测试 | 0 | 无 |
| **合计** | **1** | 计算方式：检索上游 Makefile 全部目标，仅 `lzx_test` / `lzx_test2` 一个测试程序（无 `check` / `test` 目标） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 1 | 不变（**已真实执行，1/1 通过**） | 上游 `lzx_test.c` 字节级原样复制为 `test_package/lzx_test.c`（sha256 `217d2002d7f71586ddf1d45c6fbdb1d05055fd29d7df5b4deb763c98a061dad2`，**未改动一行**），以 `lzx_test2` 目标链接 `liblzxcomp::liblzxcomp`，由 `test_package/conanfile.py::test()` 在每次 `conan create` 中真实执行（OHOS aarch64 worker 与本地 x86_64 均已跑通） |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test.c`：消费者用例，内存中构造 512KB 可压缩数据，调用真实 API `lzx_init` / `lzx_compress_block` / `lzx_finish`，断言压缩输出非空（> 4 字节长度前缀）且小于输入 |
| **合计** | **2** | **+1** | 上游 1 条（真实执行通过）+ 适配新增 1 条 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（无）

> `lzx_test.c` 以字节级原样复制进 `test_package/`（sha256 `217d2002…dad2` 与上游 tarball 中
> `lzx_compress/lzx_test.c` 完全一致），未增删一行；上游 `Makefile` 亦未改动。适配改动全部落在
> `patches/` 的 3 个补丁中，且均针对库源码（`lz_nonslide.c` / `lz_nonslide.h` / `lzx_config.h`），
> 不涉及测试断言。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无**自动化/可回归**测试，适配后补全了消费者测试

> - **补全的测试范围**：新增 1 条 `test_package/test.c` 消费者测试（鸿蒙特有测试），覆盖
>   `lzx_init → lzx_compress_block → lzx_finish` 全链路与压缩有效性断言；
>   同时把上游 `lzx_test.c` 纳入 `test_package` 随 `conan create` 每次真实执行，
>   使上游用例从"一次性手工跑过"变为"每次构建可回归"。
> - **补全原因**：上游 2005 年发行包的 `lzx_test.c` 只是一个手工 CLI 程序，没有 `check` 目标、
>   没有测试框架、没有断言与退出码语义（压缩统计仅打印到 stderr），无法作为 `conan create`
>   的可回归测试；因此按仓库规范（`ci/tools/extract_upstream_tests.sh` 第 3 步：把上游测试源
>   文件复制到 `test_package/`，在 `test()` 中编译运行）补全。
> - **新增测试文件清单**：
>   1. `archives/l/liblzxcomp/20050705/test_package/test.c` — 鸿蒙消费者测试（真实 API + 压缩断言）
>   2. `archives/l/liblzxcomp/20050705/test_package/lzx_test.c` — 上游自测程序字节级副本（未改动）
>   3. `archives/l/liblzxcomp/20050705/test_package/CMakeLists.txt` — 两个测试目标 + 确定性语料生成
>   4. `archives/l/liblzxcomp/20050705/test_package/conanfile.py` — `test()` 中执行两个测试并断言
>   5. `archives/l/liblzxcomp/20050705/reports/upstream-test-evidence.md` — 上游测试真实执行证据（含原始输出）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：**1/1（100%）**
- 新增测试用例通过率：**1/1（100%）**

### 编译验证
- 编译器: clang 15.0.7 (aarch64-unknown-linux-ohos)
- 编译状态: 通过（`conan create` 退出码 0，含 test_package 全阶段）
- 构建系统: Makefile（上游无 configure）
- 配置选项: `make CC=<clang> AR=<llvm-ar> RANLIB=<llvm-ranlib> -j1`（上游 Makefile 无 configure/install 目标，package() 直接取头文件与 `liblzxcomp.a`）

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | `liblzxcomp.a`（静态库，`lzx_layer_nonslide.o` + `lz_nonslide.o`） |
| 产物存在性 | ✅ | `conan create` 打包 `include/`（3 头文件）+ `lib/liblzxcomp.a` |
| ELF 格式 | ✅ | aarch64-unknown-linux-ohos（静态库） |
| 上游测试 | ✅ | 1/1 通过（`lzx_test2` 随 `conan create` 真实执行） |
| 运行测试 | ✅ | 2/2 通过（上游自测程序 1 + 鸿蒙消费者测试 1） |
| 动态依赖 | ✅ | 无第三方依赖（仅 `system_libs = ["m"]`） |

### 上游测试真实执行记录

上游 `lzx_test.c` 已从"仅本地跑过一次"升级为**随 `conan create` 在 CI 上每次真实执行**：

- `test_package/CMakeLists.txt` 在配置阶段用 `string(REPEAT)` + `file(WRITE)` 生成确定性语料
  `upstream_in.bin`（145600 字节，无外部命令依赖；上游 `lzx_test.c` 要求 stdin 是可 seek 的普通文件）
- `test_package/conanfile.py::test()` 执行 `"lzx_test2" 15 < upstream_in.bin > upstream_out.bin`，
  断言退出码 0、输出 > 4 字节（上游在 stdout 前置 4 字节未压缩长度）且小于输入

本地（x86_64，同一份归档）`conan create` 端到端复现，退出码 0：

```
liblzxcomp/20050705 (test package): RUN: ./test_liblzxcomp
compressed: 1372, uncompressed 524288
test liblzxcomp 20050705: OK (in=524288 out=1372)

liblzxcomp/20050705 (test package): RUN: "./lzx_test2" 15 < "./upstream_in.bin" > "./upstream_out.bin"
compressed: 896, uncompressed 163840, ratio 99.453125

liblzxcomp/20050705 (test package): upstream lzx_test.c: PASS (in=145600 out=900, ratio 99.38%)
```

> stderr 中 `uncompressed 163840` 为块对齐值（上游按 `1 << window_size` 整块读取 145600 字节输入），
> 属上游程序自身行为，非适配改动。

### 补丁说明
- `patches/0001-lz_nonslide.c.patch`: `lz_nonslide.c:191` 的 `memset(lentab, 0, sizeof(*prevtab) * chars)`
  用了指针大小（64 位 8 字节）清 `int` 数组（应为 `sizeof(*lentab)` = 4 字节），造成 2 倍堆溢出；
  上游仅在 32 位平台（`int` 与指针同为 4 字节）下意外正确，aarch64/x86_64 必须修复（bugfix）
- `patches/0002-lz_nonslide.h.patch`: 补 `typedef unsigned char u_char;`，musl/OHOS libc 不提供
  BSD 风格 `u_char`（由 sys/types.h 链提供），否则 `lzx_layer.c` / `lz_nonslide.c` 无法编译（portability）
- `patches/0003-lzx_config.h.patch`: 字节序探测改用编译器内建宏 `__BYTE_ORDER__` / `__ORDER_BIG_ENDIAN__`，
  原代码 `#if BYTE_ORDER == BIG_ENDIAN` 在无 `endian.h` 定义时两个未定义宏恒等 → `#if 0==0` 恒真，
  小端 OHOS 上误启用大端位流交换（libc 探针，符合 R8 例外口径）（bugfix）

### 依赖
- 无第三方依赖（`requirements()` 为空，`system_libs = ["m"]` 提供 `log()`）

### 遇到的问题与解决方案
1. **运行测试堆崩溃 `free(): invalid pointer` / `memset` 段错误** — 64 位堆溢出上游 bug（见补丁 0001），
   修复后同一用例在 aarch64 与 x86_64 均通过
2. **编译报 `u_char` 未定义** — musl/OHOS libc 无 BSD 风格类型（知识库 E113），补 typedef
3. **`lzx_config.h` 大小端误判** — 未定义宏使 `#if 0==0` 恒真，改用编译器内建宏
4. **Makefile 无 `install` 目标** — `package()` 用 `copy` 直取头文件与 `liblzxcomp.a`
5. **静态库链接缺 `log` 符号** — `package_info` 补 `system_libs = ["m"]`
6. **上游测试无法回归** — 上游 `lzx_test.c` 无断言/无退出码语义，已按仓库规范纳入 `test_package`
   并在 `test()` 中真实执行（见 `reports/upstream-test-evidence.md`）

### 验证命令
```bash
# OHOS aarch64 交叉构建 + 测试（CI 执行同一条命令）
conan create archives/l/liblzxcomp/20050705 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 上游自测程序等价手工复现（打全 3 个补丁的源码树）
make CC=gcc AR=ar RANLIB=ranlib -j1                     # -> liblzxcomp.a
cc -I. lzx_test.c liblzxcomp.a -lm -o lzx_test2
./lzx_test2 15 < upstream_in.bin > upstream_out.bin     # RC=0, ratio 99.45%
```

## 补充说明

- **版本号策略**：`20050705` 即上游发布版本号（FreeBSD port 的 PORTVERSION），首次适配，无修复后缀。
- **仅静态库**：上游 Makefile `all` 只产出 `liblzxcomp.a`（`.so` 由额外的 `Makefile.bsd` 打包，本适配不引入）；
  `options.shared=True` 时打印警告并仍交付静态归档。
- **`include/` 新增 `lzx_config.h`**：上游 `lzx_test.c` 依赖该头文件获取字节序宏，且本适配的补丁 0003
  正是修正该头文件，因此随包发布（消费者可复用同一份已修正的字节序探测逻辑）。
- **liblzxcomp 为纯压缩库**（上游不提供解压 API），因此无法在包内做"压缩→解压→比对"回环断言；
  压缩有效性通过"输出 < 输入且 > 4 字节"断言覆盖。
- **审计**：W4 本地独立审计 `reports/audit-result.json` 结论 `pass`（P0=0, P1=0）。
- **CI 门禁自检**：本地已同构复现 L1e 破坏性反向验证——移走包产物 `lib/` 与 `include/` 后
  `conan test` 因 `Library 'lzxcomp' not found in package` 退出码 1，证明测试真实依赖被测包。
