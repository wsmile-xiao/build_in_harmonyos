# smpq：MPQ 文件名哈希存储陷阱 与 StormLib 静态库链接顺序

> 配套结构化条目：`DRAFT-smpq-mpq-hash-filename-absolute-path-trap.kv`

## 现象

smpq/1.7 适配 HarmonyOS PC 时，test_package 驱动打包出的 `smpq` 做真实 MPQ
往返，先后踩到两类完全不同层面的问题：

1. **`--extract` 报 `File exists`**（甚至提取前目录明明是空的）；
2. 链接期 `undefined symbol`：`__gxx_personality_v0`、zlib/bzip2 符号——
   即使把 `-lz -lbz2` 塞进 `CMAKE_EXE_LINKER_FLAGS` 也照样报。

## 根因 1：MPQ 按哈希存储"传入的名字"，不是磁盘路径

`SFileAddFile` 以调用方给的名字的哈希定位归档内文件。`smpq --create
<archive> <path>` 会把 `path` **原样**当作归档内文件名：

- 用**绝对路径**建归档 → 构建机前缀（`/home/xxx/...`）被写进 listfile；
- `--extract` 按该"文件名"重建输出路径 → 试图写一个已存在的绝对路径 →
  `File exists`。

这与磁盘当前目录无关，纯属 MPQ 格式语义。

### 正确做法（消费者/测试侧）

```python
# cd 到源目录，用裸相对名建归档
subprocess.run([smpq, "--create", archive, "payload.txt"], cwd=src_dir)
# 在独立空目录里提取
subprocess.run([smpq, "--extract", archive], cwd=out_dir)
```

## 根因 2：直链静态库看不到传递依赖，且链接顺序必须"库在后"

smpq 的 CMake 用 `STORMLIB_INCLUDE_DIR` / `STORMLIB_LIBRARY` 原始变量直链
`libstorm.a`——CMake 完全看不到 StormLib 的传递依赖。StormLib 是 C++
静态库，其对象需要：

- zlib / bzip2 符号（`inflate`、`BZ2_bzDecompress` …）；
- C++ 运行期（`__gxx_personality_v0`）。

关键陷阱：`CMAKE_EXE_LINKER_FLAGS` 会被 CMake 排在**目标对象之前**，链接器
从左到右扫描时这些库还没被需要，符号照样解析不到。必须用
`CMAKE_C_STANDARD_LIBRARIES`——CMake 把它排在目标库**之后**。

另一个小坑：flag 字符串内**不能带引号**（CMake 会原样拼接）。

### 正确做法（配方侧）

```python
tc.variables["STORMLIB_INCLUDE_DIR"] = storm_include
tc.variables["STORMLIB_LIBRARY"] = libstorm_path
tc.variables["WITH_KDE"] = False          # KDE4 桌面插件与无头打包无关
tc.variables["CMAKE_C_STANDARD_LIBRARIES"] = "-lz;-lbz2;-lstdc++"  # 分号列表
```

## 附带事实

- 上游 `try_compile(check.c)` 会拒绝 StormLib < 9.14：传包内绝对路径即可满足。
- 上游**无任何测试套件**（无 `tests/`、无 CTest 目标）：消费者验证必须由
  test_package 自建完整 MPQ 生命周期（`--version` → 相对名 `--create` →
  `--info`/`--list` → 独立空目录 `--extract` → 逐字节比对）。
- StormLib 本身的 CMakeDeps 接法（`__SYS_ZLIB/__SYS_BZLIB`）与
  `SFileReadFile` 必须按精确文件长度读（EOF 返回 FALSE+1002）见
  `DRAFT-stormlib-cmake-system-libs-and-sfile-eof`。
