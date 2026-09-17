# DRAFT: musl 加载器遇 el1 沙箱目录放弃整条 LD_LIBRARY_PATH 搜索

## 现象

libcgroup 0.34（autotools）在 HarmonyOS PC 上 `conan create` 时，configure 的
AC_PROG_CXX 运行 conftest 报：

```
checking whether the C++ compiler works... yes
checking whether we are cross compiling... configure: error: cannot run C++ compiled programs.
If you meant to cross compile, use '--host'.
```

config.log 里真实错误：

```
configure:4485: ./conftest
Error loading shared library libc++_shared.so: (needed by ./conftest)
configure:4489: $? = 127
```

修好 libc++_shared.so 路径后又会轮到 `libfts.so.0`（conan host 依赖）报同样错误。

## 根因

构建机系统默认 `LD_LIBRARY_PATH` 尾部是
`/data/storage/el1/bundle/libs/arm64`——**另一个进程的应用沙箱目录**。
该目录存在、目录里也有 `libc++_shared.so`，但当前进程无权访问其内容。

musl ldso 的行为：LD_LIBRARY_PATH 中任何一个目录"存在但无法打开"时，
**整个库搜索直接失败**（报 "Error loading shared library"），而不是跳过
该目录继续搜索。因此：

- 即使把正确的 SDK 路径（含 libc++_shared.so）放在 LD_LIBRARY_PATH 最前面，
  只要 el1 段还在，加载照样失败；
- `bash -c "export LD_LIBRARY_PATH=...; ./x"`（完整继承系统默认值再拼接）
  失败，而 `LD_LIBRARY_PATH=... ./x`（命令前缀赋值，完全替换）成功——
  差异就是前者保留了 el1 段。

实验矩阵（构建机实测）：

| LD_LIBRARY_PATH | 结果 |
|---|---|
| SDK llvm/lib | ✅ 0 |
| SDK + platformsdk | ✅ 0 |
| SDK + el1/bundle/libs/arm64 | ❌ 127 |
| el1 单独 | ❌ 127 |
| /nonexistent/xyz | ✅ 0（不存在的路径无影响） |

## 修复

recipe build() 开头清洗（见 .kv 的 rec_command）。清洗后 conan create
configure 全过、make 全过、test_package 3/3 PASS。

## 关联

- E064 现象相似（conftest 无法运行）但根因不同（安全弹窗），本条是
  loader 搜索路径语义问题；
- CI profile 已带 `LD_LIBRARY_PATH=+(path)…/llvm/lib`，但**前置 ≠ 清洗**，
  el1 段仍在尾部——CI 上构建带 C++ conftest 且依赖非系统库的项目同样
  会命中。
