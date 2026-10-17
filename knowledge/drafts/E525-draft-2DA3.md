# E525: libtool -Wl 重排导致 -Bstatic 失效 — 私有静态目录方案

## 症状

在 autotools + libtool 项目中，希望把某个 conan 依赖（制品仓仅提供或同时提供
共享库）静态链入 CLI 工具时，以下两种直觉做法都会失败：

1. **`-Wl,-Bstatic -L<pkg>/lib -lzstd -Wl,-Bdynamic`（包裹对）**
   - libtool 生成最终链接命令时把所有 `-Wl,*` 参数**聚合前置**，
     `-L/-l` 留在后面：`clang -o t ... -Wl,-Bstatic -Wl,-Bdynamic -L... -lzstd`
   - 包裹对变成空操作，链接器默认动态解析 → 产物 `NEEDED libzstd.so.1`
   - 后果：工具脱离 conanrun 环境（无 LD_LIBRARY_PATH）执行报
     `Error loading shared library libzstd.so.1` → exit 127
2. **`ZSTD_LIBS=/abs/path/libzstd.a`（绝对路径）**
   - libtool 把 .a 路径当作 convenience library，构建 libsquashfs.a 时把整个
     归档**嵌套拷贝**进产物
   - 最终链接时 ld.lld 报 `archive member 'libzstd.a' is neither ET_REL nor
     LLVM bitcode` + `undefined symbol: ZSTD_*`

## 根因

libtool 的参数处理语义：`-Wl` flag 聚合重排 + convenience library 拷贝。

## 解决方案（private-static-libdir）

在 `generate()` 中：

1. 复制依赖的静态库到 build_folder 下的私有目录（**目录中不含任何 .so**）：
   `build_folder/zstd_static/libzstd.a`
2. 依赖注入变量（如 `ZSTD_LIBS`）只指向私有目录：`-L<private> -lzstd`
3. **同时从 `AutotoolsToolchain.extra_ldflags` 中排除该依赖的原 libdir**——
   链接器按 -L 出现顺序搜索，原目录（含 .so）在前会先命中

```python
zstd_static_dir = os.path.join(self.build_folder, "zstd_static")
os.makedirs(zstd_static_dir, exist_ok=True)
for libdir in zstd_dep.cpp_info.libdirs:
    src = os.path.join(libdir, "libzstd.a")
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(zstd_static_dir, "libzstd.a"))
        break
env.define("ZSTD_LIBS", f"-L{zstd_static_dir} -lzstd")
```

## 验证

```bash
readelf -d <pkg>/bin/<tool> | grep NEEDED   # 应只有 libc.so，无 libX.so
env -i PATH=$PATH <pkg>/bin/<tool> --version  # 裸环境直执应成功
```

## 案例

- squashfs-tools-ng 1.3.2（PR #6230）：zstd/1.5.6 与 1.5.7 仅含 .so，
  zstd/1.5.7.1 首个含 libzstd.a；升级依赖 + 私有目录方案后 5 个 CLI 工具
  NEEDED 仅 libc.so，L2 平台冒烟（裸环境直执）全部通过
