# DRAFT-13952 — 无 pkg-config 环境下 PKG_CHECK_MODULES 的环境变量短路三件套

> 草稿状态：pending-editor-review（拟提升编号由主编确认，草稿以 PR 号命名占位）
> 来源：libwps 0.4.11 适配 PR #13952（j669539，鸡屁股队）——继承 libwpd 0.10.3 设备实证经验

## 错误特征

```
Package librevenge-0.0 was not found in the pkg-config search path
checking for REVENGE... no
configure: error: Package requirements (librevenge-0.0) were not met

libtool: warning: library '.../librevenge-0.0.la' was moved.
libtool: error: cannot find the library '//lib/librevenge-0.0.la'

ld: archive member '.../librevenge-0.0.a' is neither ET_REL nor LLVM bitcode

undefined reference to `inflate'
```

## 触发条件

- 构建系统：autotools（configure.ac 使用 PKG_CHECK_MODULES 宏）
- 环境：OHOS 设备/CI Worker——**没有 pkg-config 可执行文件**
- 依赖形态：conan 静态依赖包（.a + .la + versioned includedir）
- 阶段：configure 探测 / make 链接 / test() 直跑目标二进制

## 根因分析

三个相互叠加的陷阱，单独用任何一个手段都不够：

1. **PKG_CHECK_MODULES 默认探测失效**：pkg.m4 宏在 host 无 pkg-config 时直接报
   "was not found in the pkg-config search path"。但 pkg.m4 有个设计行为——
   `<PREFIX>_CFLAGS` / `<PREFIX>_LIBS` 环境变量**非空时直接采信**，跳过 pkg-config
   探测。这就是短路点。
2. **libtool 对 .la 的优先解析**：conan 包内 .la 记录的是安装期 libdir
   （prefix=/ + DESTDIR = `//lib` 绝对路径）。`-L` 指向包 lib 目录时 libtool 优先找
   `.la` 并按其内记录路径链接 → "was moved / cannot find"。改用 .a 绝对路径直传
   虽然绕开 .la，但 libtool 会把 .a 当**输入成员**嵌进正在构建的静态库
   （"neither ET_REL nor LLVM bitcode"），且与消费者后续链接的同一 .a 冲突。
3. **静态闭包不进 .pc 递归**：librevenge 的流层静态链 zlib（-lz），但
   PKG_CHECK_MODULES 只喂 -lrevenge-0.0 时消费者链接缺 inflate 系列。
   闭包必须手工补进 `_LIBS` 尾部。

## 解决方案（三件套，均在 conanfile.py）

### 1) PKG 变量短路：configure 环境导出三组 `<PREFIX>_CFLAGS/_LIBS`

```python
def _pkg_vars(self):
    revenge = self.dependencies["librevenge"].package_folder
    zlib = self.dependencies["zlib"].package_folder
    include = f"-I{revenge}/include/librevenge-0.0"
    link_zlib = f"-L{zlib}/lib -lz"          # 静态闭包：librevenge 流层链 zlib
    link_dir = self._clean_link_dir()
    link = f"-L{link_dir}"
    return {
        "REVENGE_CFLAGS": include,
        "REVENGE_LIBS": f"{link} -lrevenge-0.0 {link_zlib}",
        "REVENGE_GENERATORS_CFLAGS": include,
        "REVENGE_GENERATORS_LIBS":
            f"{link} -lrevenge-generators-0.0 -lrevenge-0.0 {link_zlib}",
        "REVENGE_STREAM_CFLAGS": include,
        "REVENGE_STREAM_LIBS":
            f"{link} -lrevenge-stream-0.0 -lrevenge-0.0 {link_zlib}",
    }
```

注意：每个 `PKG_CHECK_MODULES([PREFIX],[pkg])` 调用对应一组变量；前缀名查
configure.ac 原文。多包依赖（如本例 generators/stream）需把基础库重复放进
依赖它的 `_LIBS`。

### 2) .la-free 干净链接目录（E236 同款复用）

```python
def _clean_link_dir(self):
    clean = Path(self.build_folder, ".revenge-libs")
    clean.mkdir(parents=True, exist_ok=True)
    for name in ("revenge-0.0", "revenge-generators-0.0", "revenge-stream-0.0"):
        source = Path(self._revenge_archive(name))
        destination = clean / source.name
        if not destination.exists():
            copy(self, source.name, src=str(source.parent),
                 dst=str(clean), keep_path=False)
    return clean
```

构建私有目录只放 .a 不放 .la，`-L` 指向它后 libtool 走纯 `-L/-l` 解析，
既不会误读 .la 也没有成员嵌入问题。conan 缓存原包不动。

### 3) test() 直跑 OHOS 二进制补 /system/lib64

```python
def test(self):
    cmake = CMake(self); cmake.test()      # ctest 在 conanbuild env 下跑（有 profile LD_LIBRARY_PATH）
    environment = Environment()
    if os.path.isdir("/system/lib64"):
        environment.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
    with environment.vars(self).apply():
        ...  # 直跑测试二进制/转换工具：conanrun env 不带 profile 的 LD_LIBRARY_PATH，
             # 而 OHOS 目标二进制的 libc++.so（__h-namespace 构建）在 /system/lib64
```

## 降级方案（fallback）

- 上游不用 PKG_CHECK_MODULES 标准变量名：patch configure.ac 换 AC_CHECK_HEADERS/
  AC_CHECK_LIB 显式探测；
- host 侧有真 pkg-config 可用时：写包装脚本挂 `PKG_CONFIG` 环境变量；
- 依赖只发 .la 无 .a：按 E236 在打包阶段清理/重写 .la 的 libdir 字段。

## 红线

- 禁止把 `.a` 绝对路径直接塞进 LIBS（libtool 成员嵌入陷阱）；
- 禁止删 conan 缓存里的 .la（影响其他消费者），只用构建私有干净目录；
- `-lz` 闭包项不能省——.pc 递归不携带静态闭包。

## 实证

- verify_builds: #13952（CI 构建 #65484 PASSED；本机 conan create 全绿 RC=0）
- 同族先例：libwpd 0.10.3（本作者适配）；.la 规避同款方案 E236（PCRE2/SQLite3 LIBADD 案例）

## 与现有知识的关系（查重结论）

- **E236（scoped-la-free-static-archive-directory）**：本条方案 2 复用其 .la-free
  思路，但 E236 场景是"构建中 Libtool 静态库吃依赖"，本条是"无 pkg-config 环境
  PKG_CHECK_MODULES 整体短路"的组合母题，含变量短路与静态闭包两个 E236 未覆盖点。
- **E075（env-var-remove）**：E075 讲"环境变量污染要删"，本条相反——讲"哪些环境
  变量要**主动导出**才能短路宏探测"，方向互补不覆盖。
- **E120/E132（LD_LIBRARY_PATH 链接/加载）**：讲链接期与工具链库路径，本条方案 3
  是 test() 运行期 conanrun env 缺口的精准补法（conanrun vs conanbuild env 差异）。
