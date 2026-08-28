# libquantum 1.0.0 适配笔记

## 编译环境
- 构建系统: autotools（上游 `configure` + `Makefile.in` + `libtool`，未重写）
- 编译日期: 2026-08-27
- 编译器: clang 15.0.4 (OHOS 工具链, target aarch64-unknown-linux-ohos)
- 状态: built
- 目标平台: OpenHarmony / HarmonyOS PC aarch64 (armv8)

## 上游信息

- 官方主页: http://www.libquantum.de/
- 官方源码: http://www.libquantum.de/files/libquantum-1.0.0.tar.gz
- SHA256: `b0f1a5ec9768457ac9835bd52c3017d279ac99cc0dffe6ce2adf8ac762997b2c`
  - 与 Homebrew formula (`Formula/lib/libquantum.rb`)、pkgsrc distinfo
    (BLAKE2s/SHA512) 交叉验证一致。
- 许可证: GPL-3.0-or-later（见 `COPYING`，GPLv3 全文）
- 压缩包大小: 223241 字节

## 源码结构

```
libquantum-1.0.0/
├── configure.in / configure / aclocal.m4   # autotools 构建系统
├── Makefile.in                              # 上游 Makefile 模板
├── config.h.in / quantum.h.in / types.h.in  # autotools 输出头模板
├── ltmain.sh / config.guess / config.sub    # libtool + autotools 辅助
├── install-sh                                # install 辅助
├── COPYING                                   # GPLv3 全文
├── README / INSTALL / CHANGES
├── quantum.h.in                              # ★ 对外 API 头文件模板
│   (生成 quantum.h: quantum_reg, quantum_new_qureg, quantum_hadamard,
│    quantum_sigma_x, quantum_cnot, quantum_measure, quantum_bmeasure,
│    quantum_qft, quantum_get_version 等)
├── qureg.c / qureg.h          # 量子寄存器核心
├── gates.c / gates.h          # 门操作 (Hadamard/CNOT/Pauli/phase/QFT)
├── measure.c / measure.h      # 量子测量
├── matrix.c / matrix.h        # 复数矩阵
├── complex.c / complex.h      # 复数运算
├── decoherence.c / density.c  # 退相干/密度矩阵
├── qec.c / qft.c / qtime.c    # 量子纠错/QFT/时间演化
├── classic.c / oaddn.c / omuln.c / expn.c  # 经典算术门
├── objcode.c                  # 量子目标代码
├── error.c / version.c        # 错误处理/版本
├── grover.c / shor.c          # ★ Grover/Shor 算法演示 (有 main())
├── quobprint.c / quobdump.c   # 量子目标代码工具 (有 main())
└── defs.h / expn.h / ...      # 内部头文件
```

## 真正需要打包的核心内容

1. **`quantum.h`** — 对外 API 头文件（由 `quantum.h.in` 经 configure 生成）。
   定义 `MAX_UNSIGNED`、`COMPLEX_FLOAT`、`quantum_reg`、`quantum_matrix`、
   `quantum_density_op` 结构体，以及全部公开 API 声明：
   `quantum_new_qureg`、`quantum_delete_qureg`、`quantum_hadamard`、
   `quantum_sigma_x/y/z`、`quantum_cnot`、`quantum_toffoli`、`quantum_qft`、
   `quantum_measure`、`quantum_bmeasure`、`quantum_decohere`、
   `quantum_get_version` 等。安装到 `include/`。
2. **`libquantum.a`** — 静态库（libtool 构建 `libquantum.la`，静态产物为
   `.a`）。消费者链接此库 + libm 即可使用全部量子模拟功能。

> grover/shor/quobprint/quobdump 是演示和工具程序（有独立 main()），
> 非库的核心 API，不打包（避免 bin/ 污染）。

## 上游测试分析

上游**无正式测试套件**。证据：

1. **Makefile.in 无 `check`/`test` target** — 全部 target 为：
   `all`、`demos`(shor/grover)、`quobtools`、`quobprint`、`quobdump`、
   `install`、`quobtools_install`、`clean`、`distclean`、`dist`。
2. **无 test/ 或 tests/ 目录** — `find` 确认源码树无任何 test 相关文件。
3. **configure.in 无测试逻辑** — 仅 AC_CHECK_LIB([m],[sqrt])、
   AC_HEADER_STDC、AC_CHECK_HEADERS、AC_C_INLINE、64位整数/复数类型检测，
   无 AC_CHECK_FUNCS 测试或 test target。
4. **grover.c / shor.c** 是 Grover/Shor 算法的演示程序（含独立 main()），
   非自检型单元测试，运行结果依赖随机种子且无断言。
5. **README / INSTALL / CHANGES** 均无 test/check/verify 相关引用。

因此：
- 上游测试数 (Total): **0**
- 通过 (Pass): **N/A**
- 失败 (Fail): **N/A**
- 跳过 (Skip): **N/A**

按任务要求，不因上游无测试就虚构；新增的 test_package consumer 调用
核心 API 并做断言，作为**集成测试**（共 12 条断言）。

## 编译步骤

复用上游 autotools，通过 Conan AutotoolsToolchain 完成 OHOS 交叉编译，
**不打补丁**：

```bash
# Conan AutotoolsToolchain 注入 profile 的 OHOS clang：
#   CC=<profile-resolved clang> (aarch64-unknown-linux-ohos)
# configure 检测到 clang，生成 Makefile / quantum.h / types.h / config.h
./configure --prefix=<pkg> --enable-static --disable-shared
make -j
make install DESTDIR=<pkg>
```

- `--enable-static --disable-shared`：libquantum 的 `make install` 会安装
  同名 `.so` 到系统 lib 路径（S2 约束），默认静态避免污染 sysroot。
- `DESTDIR` 由 Autotools.install() 设置为 package_folder，quantum.h →
  include/，libquantum.a → lib/。

## 依赖

- **libm**（系统库）— configure.in `AC_CHECK_LIB([m],[sqrt])`，Makefile.in
  链接 `-lm`。OHOS musl libc 提供 libm，无需第三方依赖。
- 无其他外部依赖（源码 `#include` 仅标准 C 头 + 自有头 + math.h）。
- recipe 用 `system_libs = ["m"]` 表达，不声明任何 `requires()`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 静态库同名 .so 污染 sysroot | libtool 默认构建 shared+static，`make install` 安装 .so 到 lib/ | configure 加 `--enable-static --disable-shared`，仅产 .a (S2) |
| 2 | libtool .la 残留 | libtool 生成 .la 辅助文件，消费者不需要 | package() 中 `rm *.la` 清理 |

> 以上均通过 **configure 参数 / recipe** 解决，未使用任何 patch（符合零 patch 要求）。

## 源码修改

无。未应用任何补丁（`patches: []`）。

## 依赖版本

- libm（系统库，OHOS musl libc 自带）
- 无第三方 Conan 依赖

## 验证结果

```bash
# conan create（OHOS profile）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → libquantum.a + quantum.h 打包成功

# test_package
# → consumer 构建 test_quantum，创建 2-qubit 寄存器，执行 Hadamard + Pauli-X
#   门操作，验证概率幅归一化，执行单 qubit 测量验证坍缩，12 条断言全通过

# ELF 验证
# → libquantum.a 内目标文件 readelf: ELF64 AArch64, OS ABI = ARM64 (OHOS musl)
```

## 交付物

| 文件 | 说明 |
|------|------|
| include/quantum.h | 核心 API 头文件 |
| lib/libquantum.a | 静态库 |
| licenses/COPYING | GPLv3 许可证 |
| licenses/README | 上游 README |

## 注意事项

- libquantum 是纯 C 库，无 C++ 依赖，无第三方 Conan 依赖。
- `quantum.h` 由 configure 从 `quantum.h.in` 生成，包含平台相关的
  `COMPLEX_FLOAT`/`MAX_UNSIGNED`/`IMAGINARY` 宏定义（OHOS 上为
  `float _Complex` / `unsigned long long` / `_Complex_I`）。
- 静态链接时消费者需额外链接 `-lm`（由 `system_libs` 自动注入）。

---

**编译结束**: 2026-08-27
**最终状态**: built
