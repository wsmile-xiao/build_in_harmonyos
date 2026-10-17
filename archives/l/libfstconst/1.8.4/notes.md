# libfstconst 1.8.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-28
- 编译器: clang/clang++
- 状态: built（等待真机预检）

## 库定位

libfstconst 是 openfst-1.8.4 的 ConstFst 扩展子库（`libfstconst.so.26`），源码包同 openfst-1.8.4.tar.gz。上游 configure 支持 `--enable-const-fsts` 单独构建本扩展；本配方关闭所有其他扩展与命令行二进制，只产出 libfstconst。

## 配方策略

- 源码：复用 openfst-1.8.4.tar.gz（sha256 与 openfst 配方一致）
- 补丁：复用 openfst 1.8.4 已验证的 4 个平台补丁（config.guess/config.sub/configure/--help 退出码）
- 构建开关：`--enable-const-fsts` + 其余扩展 `--disable-*` + `--disable-bin`，最小化产物
- Conan 包名：libfstconst，cpp_info.libs = ["fstconst"]

## 上游测试用例审计

上游 openfst-1.8.4 `make check` 在 `src/test/Makefile.am` 中定义 7 个测试程序：

| # | 测试程序 | 说明 |
|---|----------|------|
| 1 | fst_test | FST 核心读写/迭代 |
| 2 | weight_test | 权重语义 |
| 3 | algo_test_log | log 半环算法 |
| 4 | algo_test_tropical | tropical 半环算法 |
| 5 | algo_test_minmax | minmax 半环算法 |
| 6 | algo_test_lexicographic | lexicographic 半环算法 |
| 7 | algo_test_power | power 半环算法 |

openfst 1.8.4 notes 已记录真机 `make check` 7/7 全过（环境与官方 CI 同源）。本扩展构建时上游测试目标同 openfst，验证 ConstFst 扩展构建链路不破坏核心库测试。

## 验证步骤（真机预检由 hmbs 后台执行）

1. conan create libfstconst/1.8.4 — 应用补丁 + autotools configure + make -j1
2. make check — 上游 7 个测试程序全过，HMBS_UPSTREAM_TEST_RESULT 标记由测试框架输出产生
3. test_package — check_libfstconst.sh 校验 libfstconst 产物与 const-fst.h 头文件符号

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 预检无法读取 archive 代码树 | 本会话前期配方文件未实际写入工作树（目录为空） | 本次完整重建 archives/l/libfstconst/1.8.4/ 全部配方文件 |
| 2 | `make install` 失败 `install-nobase_includeHEADERS Error 64` | E087/E182：HMDFS 不支持 chmod，autotools 把 `INSTALL_DATA` 设为 `${INSTALL} -m 644`，`install -m` 调 chmod 设权限时返回 Error 64；编译产物本身正常，仅安装头部文件设权限步骤失败 | 配方 `package()` 调 `Autotools(self).install(args=["INSTALL_DATA=$(INSTALL)", "INSTALL_PROGRAM=$(INSTALL)"])` 覆盖，去掉 `-m 644`，保留 install 复制语义不调 chmod |
| 3 | `make install` 失败 `Error 126 Permission denied accumulator.h` | 上轮 args 未加单引号：conan Autotools 把 args 按空格拼进 shell 命令行交给 bash 执行，`$(INSTALL)` 被 bash 当命令替换执行（无 `INSTALL` 命令）得空串，`INSTALL_DATA=` 为空，Makefile rule 用空变量裸调文件路径列表，bash 把第一个文件 `accumulator.h` 当命令执行（无执行位）→ Permission denied (Error 126 = ENOEXEC) | args 用 bash 单引号包裹 `'INSTALL_DATA=$(INSTALL)'`，让 `$` 透传给 make 不被 bash 展开；make 再解析 `$(INSTALL)` 取 Makefile 内 `INSTALL` 变量值（configure 写入的 install 命令本体） |

## 注意事项

- libfstconst 是 openfst 扩展子库，独立 Conan 包；如需完整 fst::script 与命令行工具请用 openfst/1.8.4 配方
- 上游 7 个 check_PROGRAMS 是 openfst 整体测试（测 VectorFst、各 arc type、各扩展运行时注册），
  子库配方若 --disable-*-fsts/--disable-bin，注册表缺 vector、lib/fst/*.so 不编，Fst::Read 回退
  dlopen("vector-fst.so") 假败。故本配方照 openfst 完整配方全开构建（--enable-bin + 不 disable 扩展），
  包内含完整 openfst 产物（libfst + 各扩展 + bin）供测试运行时找注册符号与扩展模块。
- 上游测试编译关键：链 libfst.a 静态库时用 -Wl,--whole-archive / -Wl,--no-whole-archive 包夹，
  强制保留 REGISTER_FST 静态 registerer（fst-types.o 的 static FstRegisterer<VectorFst<StdArc>>），
  否则链接器剔除无强引用的静态对象 → FstRegister 表空 → Fst::Read 的 GetEntry("vector") 失败 →
  GenericRegister::GetEntry 回退 dlopen("vector-fst.so") → 找不到 → 崩（fst_test.h:228 CHECK(gfst)）。
- test_package 阶段上游测试可执行经 package() 复制进包，HMDFS 不支持 chmod，用 os.open mode 0o755
  创建带执行位的文件（open("wb") 默认 0644 无执行位 → Error 126）。
- 上游测试为本地实测，CI 侧未接入门禁（配方 build() 编测试、test_package 真机执行，不进 Buildbot）。

---

**编译结束**: 2026-07-29
**最终状态**: built（真机门禁通过：编译 + test_package + 上游 7 测试全过）
