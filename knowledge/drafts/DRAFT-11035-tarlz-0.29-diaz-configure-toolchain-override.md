# DRAFT-11035-tarlz-0.29-diaz-configure-toolchain-override：Diaz 手写 configure 系三连坑——make 命令行覆盖三件套闭环

> Contributor: Ember5843 | Status: Draft | Updated: 2026-09-28
> Source: tarlz 0.29 适配（ohpcd id=11035，feat/tarlz-0.29）；设备 5 轮迭代实锤
> 对应：`knowledge/drafts/DRAFT-11035-tarlz-0.29-diaz-configure-toolchain-override.kv`

## 现象

Antonio Diaz 系工具（tarlz/lzip/lzlib 同构模板）设备构建连环失败，每轮修一个冒下一个：

```text
轮1: KeyError: 'sources' / KeyError: 'url'      ← conandata 层级与配方取法错位（本包问题，非上游）
轮2: OHOS build step failed (rc=127): lzip -d   ← tool_requires 的二进制不在 raw subprocess PATH 上
轮3: umask contract changed: no 'umask 077'     ← autoconf 系 fail-fast 契约误杀 Diaz configure
轮4: make: c++: No such file or directory       ← 生成 Makefile 写死 CXX=c++，无视环境
轮5: fatal error: 'lzlib.h' file not found      ← Makefile 只保留自己的 -O2，环境 CPPFLAGS 被丢弃
```

最迷惑的是轮 5：configure 的 lzlib 探针是**过**的（"OK. Now you can run make"），make 却找不到头——因为探针用的是环境 CPPFLAGS，而生成 Makefile 编译行根本不用它。

## 根因（机制链）

Diaz 不用 autoconf，用手写 configure + Makefile.in 模板，三处与 autoconf 生成物行为不同：

1. **官方独家 .tar.lz 包**：发布目录是 `releases/lzip/tarlz/`（`releases/tarlz/` 不存在，直接 404）。conan 2.32 的 `unzip_and_get` 只认 .tar.gz/.tgz/.tbz2/.tar.bz2/.tar/.tar.xz/.txz/.tar.zst/.tzst——`.tar.lz` 不在名单，调 `get()` 直接抛错。
2. **Makefile 硬编码编译器**：`CXX = c++` / `CC = cc` 写死，不读环境。conan profile 给的 clang++ 完全被无视，设备上没有 `c++` → Error 127。
3. **Makefile 丢弃环境标志**：编译行只有自己的 `-O2`，`$(CPPFLAGS)` 根本没出现在规则里（可用 `grep -n CPPFLAGS Makefile` 验证，真没有）。

附带：该 configure 内无 `umask 077`（Diaz 不建 autoconf 式 scratch dir），autoconf 系的 hmdfs 改写 fail-fast 在此是误杀，实测 count=0 为真值。

## 方案（make 命令行覆盖三件套）

```python
# 解包：source() 只下载+验签；build() 内手动解
self.tool_requires("lzip/1.25")  # 制品仓已发布
# build env 必须显式注入 tool bindirs（raw subprocess 看不到）：
for dep in self.dependencies.build.values():
    for bindir in dep.cpp_info.bindirs:
        environment.prepend_path("PATH", bindir)
# 编译器+标志：make 命令行一次性覆盖（Diaz 模板无 override 指令，命令行赋值必胜）：
make -j1 CC=<profile-cc> CXX=<profile-cxx> CXXFLAGS="-O2 <deps -I…>" LDFLAGS="<deps -L…>"
# umask：无 umask 077 时 warning 跳过，不 fail-fast
```

设备验证：`TARLZ_TEST PASS`（7 断言 roundtrip）+ `CREATE_RC=0`；上游 `make check` 8 命名组全过，6 处 "Mode differs" 为 hmdfs mode 位语义（内容逐字节一致），见包 notes.md R51 记账。

## 适用边界

- Diaz 全系（tarlz/lzip/lzlib/lunzip/xlunzip 同构模板）；
- 任何"configure 探针过、make 找不到头/库"的包，先 `grep -n CPPFLAGS 生成的Makefile`——没有即本模式；
- 与 autoconf 系包（如 tardy）的 umask fail-fast 契约**不可混用**，见 forbid_3。
