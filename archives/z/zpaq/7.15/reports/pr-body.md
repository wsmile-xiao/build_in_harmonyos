- **三方库名称**：zpaq
- **上游版本**：7.15
- **上游仓库地址**：https://github.com/zpaq/zpaq（作者 Matt Mahoney 的官方仓库）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（W2→W5 流程门禁）；知识命中并复用：libzpaq 0.01 的 `libc++_shared.so` 链接器脚本坑（`-static-libstdc++` 对策）；本 PR 新增 2 条知识草稿：`knowledge/drafts/zpaq-7.15-nojit-aarch64-sigill.{kv,md}`、`knowledge/drafts/zpaq-7.15-no-version-flag-smoke-gate.{kv,md}`

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无单元测试框架（无 tests/ 目录、无 CTest/gtest 注册） |
| 集成测试 | 0 | - |
| 其他测试（`make check`） | 1 | 顶层 `Makefile:32-36`：`add` → `extract -to` → `cmp` 往返，1 条断言 |
| **合计** | **1** | 本仓 R51 口径：注册用例数 = 断言数（`cmp` 一条） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 1 | 不变 | 上游 `make check` 适配机实测 **1/1 通过** |
| 鸿蒙特有测试 | 7 | 新增 | `test_package/test.sh` 对安装出来的 `bin/zpaq` 实测 **7/7 通过**（含完整消费者用例：真实归档往返、字节级 cmp、`-until 1` 版本回滚、跨版本去重记账、增量归档、错误诊断，非纯断言） |
| **合计** | **8** | **+7** | 上游 1 + 鸿蒙特有 7，全部通过 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

> 无补丁。上游源码为 2016 年发布的原样 C++（纯 ISO C++ + POSIX pthread），零修改即可在
> aarch64 OHOS 上编译运行；`conandata.yml` 的 `patches:` 为空，`apply_conandata_patches()`
> 是空操作。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无独立测试框架，适配后补全了测试

> - **补全的测试范围**：为交付包新增 7 个鸿蒙特有消费者用例（`test_package/test.sh`），
>   覆盖安装产物的真实 CLI 行为：T1 版本横幅、T2 归档往返字节一致、T3 日志式多版本、
>   T4 历史版本回滚、T5/T5b 片段去重与增量记账、T6 错误诊断。
> - **补全原因**：上游仅一条 `make check` 收尾断言（1 条 `cmp`），且不含任何测试框架；
>   依赖 `<tool> --version` 的通用冒烟门禁对本包不适用（zpaq 无 `--version`/`--help`，
>   退出码为三态：usage=1、缺归档=2、缺输入路径=0），必须用真实归档往返断言替代
>   （知识草稿 `zpaq-7.15-no-version-flag-smoke-gate`）。
> - **新增测试文件清单**：
>   1. `archives/z/zpaq/7.15/test_package/test.sh` — 7 条消费者断言（`set -euo pipefail`，
>      期望失败的调用逐条 `rc=0; cmd || rc=$?` 捕获，诊断文本 + 退出码一起断言）
>   2. `archives/z/zpaq/7.15/test_package/conanfile.py` — 解释器解析：
>      `$CONFIG_SHELL`（须指向存在的文件）→ 固定候选清单 `os.path.exists()` 探测 →
>      都取不到即 `ConanException`（不用 `shutil.which("bash")`：实测会命中调用方运行时
>      自带 bash，`/system/bin/sh` 执行报 Permission denied，`test()` Error 126）

## 验证结果

- 编译状态：**通过**（clang 15.0.4，`aarch64-unknown-linux-ohos`；构建等价上游
  `Makefile:32-36` 的 `zpaq` 目标：`-O3 -DNDEBUG -Dunix -DNOJIT -static-libstdc++`，
  零依赖，产物 `bin/zpaq` + `licenses/COPYING`）
- 上游测试用例通过率：**1/1（100%）**（适配机实测，非声明）
- 新增测试用例通过率：**7/7（100%）**（`conan create` 内 `test()` 实测）

### 产物验证

| 项 | 结果 | 说明 |
|----|------|------|
| 编译无错误 | PASS | `conan create` 成功，状态 built |
| 产物存在性 | PASS | 包内 `bin/zpaq` + `licenses/COPYING` |
| ELF 格式 | PASS | `ELF 64-bit LSB shared object, ARM aarch64`（PIE / GNU_RELRO / BIND_NOW / 栈不可执行） |
| 动态依赖 | PASS | `DT_NEEDED` 仅 `libc.so`（libc++ 已静态烘焙），无 RPATH/RUNPATH |

### 依赖

零依赖（`requirements()` 为空）。系统侧仅 pthread —— 由上游 `-pthread` 提供，
OHOS musl 的 pthread 在 libc 内，无需额外 Conan 包。

## 补充说明

### 遇到的问题与解决方案

1. **`-DNOJIT` 不能省（必需）**：`libzpaq.cpp` 的 `ZPAQL::assemble()`（3035-4585 行）
   在运行期生成 x86-32/x86-64 机器码并跳转执行。aarch64 上不加该宏**能编译、也能压缩**，
   但一走到解压即 `Illegal instruction (core dumped)` —— 属「能编过但不可用」的隐性失败。
   解决：构建时加 `-DNOJIT`，走可移植解释器 `predict0()`。
2. **动态链接的 `zpaq` 起不来**（`Error loading shared library libc++_shared.so`）：
   OHOS SDK sysroot 的 `libc++_shared.so` 是链接器脚本（`INPUT(-lc++_shared)`），
   musl 加载器无法解析。解决：`-static-libstdc++` 静态烘焙 libc++，产物只依赖 `libc.so`。
3. **`-march=native` 不可用**：编译目标是 `aarch64-unknown-linux-ohos`，与宿主 CPU 不匹配，
   且会破坏包的可移植性。解决：覆盖 `CXXFLAGS`，去掉该选项。
4. **recipe shell 为 `/system/bin/sh` 时编译器静默退出 1（本次最耗时的问题）**：
   编译器 stdio 直连 CI harness 捕获管道时退出码 1 且**零诊断输出**；同一条命令把 stdio
   落到普通文件即 `rc=0`（受控 A/B 实验）。解决：编译输出重定向到 `zpaq-build.log` 再
   `cat` 回显，并改用单次直接编译调用（不依赖 recipe shell 的具体实现），
   同时以 `exit $rc` 保留返回码。
5. **`conandata.yml` 注释里的仓库地址会被 CI 的 URL 重写误伤**：mirror-fallback 与
   Pre-download 按「文件内出现的**全部** URL 字面量」做 `str.replace`，注释里的裸仓库地址
   是 tarball 地址的前缀，替换后 `sources.url` 被改写成畸形 `file://` 路径，
   `source()` 报 `NotADirectoryError`。解决：conandata.yml（含注释）只保留 `sources.url`
   一处 URL 字面量，官网/仓库地址改写为不含 scheme 的文字描述。
6. **`test_package` 解释器解析**：不可用 `shutil.which("bash")` —— 实测会命中调用方运行时
   自带的 `/data/storage/el1/bundle/.../bash/bin/bash`，`/system/bin/sh` 执行它报
   `Permission denied`，`test()` 以 `Error 126` 中断。解决：`$CONFIG_SHELL`（须指向存在的
   文件）→ 固定候选清单 `os.path.exists()` 探测 → 都取不到即 `ConanException` 显式报错。

### conan-verify 门禁口径（如实记录）

| 门禁 | 工具输出 | 本包记录 |
|------|---------|---------|
| G0-G3 | PASS | PASS（G0 的依赖预查询因构建系统识别为 unknown 被工具跳过；本包零依赖无预查询可执行） |
| G4 | `✅ PASS` + `⚠️ 无法找到程序包 ID` | **SKIPPED**（工具未执行，application 包无 `lib/`，同 bti 034 现象） |
| L2 / L4 / L5 | `✅ PASS` + `⏭️ 跳过（无 cache 路径）` | **SKIPPED**（工具未执行） |

按「PASS 与 SKIP 并存时以 SKIP 为准」的口径，G4/L2/L4/L5 记为**未执行、不计入通过**，
由 `reports/conan-verify-supplement.md` 的人工补测覆盖：
G4 产物清单（4 项，与 `package_info()` 一致）、L2 消费者实测（包内二进制 7/7）、
L4 ELF 安全属性（PIE / 栈不可执行 / RELRO / BIND_NOW / 仅依赖 libc.so）、
L5 两轮独立清缓存构建复现基线（`bin/zpaq`、`conaninfo.txt`、`licenses/COPYING` 逐字节一致，
仅 `conanmanifest.txt` 首行打包时间戳漂移）。

### 已知限制

上游 7.15 无 `--version` / `--help` 开关，`conan-verify` 的 L2 冒烟判据
（`bin --version` 退出码 0）对本包不适用，已用真实归档往返断言替代（详见 notes.md
与知识草稿 `zpaq-7.15-no-version-flag-smoke-gate`）。

### 验证命令

```
# 1) 上游测试（适配机实测 1/1）
make check CXX=clang++ CPPFLAGS="-Dunix -DNOJIT" CXXFLAGS="-O3 -DNDEBUG" LDFLAGS="-static-libstdc++"

# 2) 交付包消费者实测（7/7；脚本对安装出来的 bin/zpaq 做真实归档往返/回滚/去重/错误路径断言）
conan create archives/z/zpaq/7.15 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 3) 本地 CI 模拟（阻塞门禁，已通过）
zsh ci/conan/build_and_test.sh archives/z/zpaq/7.15

# 4) 产物属性
llvm-readelf -dW <pkg>/bin/zpaq | grep NEEDED      # 仅 libc.so
```

逐字日志见 `reports/test-report.md`、`reports/conan-create.log`、`reports/w3-local-ci.log`。
