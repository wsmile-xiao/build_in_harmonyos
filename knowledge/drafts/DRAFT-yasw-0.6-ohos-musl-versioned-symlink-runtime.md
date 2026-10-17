# DRAFT-yasw-0.6-ohos-musl-versioned-symlink-runtime：OHOS 加载器不跟随 `.so` 版本化符号链接

> Contributor: ohc-worker | Status: Draft | Updated: 2026-09-21
> Source: yasw 0.6 适配（依赖 `qt/5.15.19.1`；qt 包内 `lib/libQt5*.so.5` 为符号链接）
> 对应：`knowledge/drafts/DRAFT-yasw-0.6-ohos-musl-versioned-symlink-runtime.kv`
> 相关：`DRAFT-E5xx-registry-so-baked-absolute-needed-symlink`（**相关但解法相反**，见末节）

## 现象

以 conan 包目录作为 `LD_LIBRARY_PATH` 直接运行产物 → 退出码 **127**：

```console
Error loading shared library libQt5PrintSupport.so.5: (needed by <pkg>/bin/yasw)
Error loading shared library libQt5Widgets.so.5:      (needed by <pkg>/bin/yasw)
Error loading shared library libQt5Gui.so.5:          (needed by <pkg>/bin/yasw)
Error loading shared library libQt5Xml.so.5:          (needed by <pkg>/bin/yasw)
Error loading shared library libQt5Core.so.5:         (needed by <pkg>/bin/yasw)
Error relocating <pkg>/bin/yasw: _ZN12QApplicationC1ERiPPci: symbol not found
```

而包内**确实存在**这些文件（版本化符号链接，目标真实且可读）：

```console
$ ls -la <qt-pkg>/lib/ | grep libQt5Core
lrwxrwxrwx  libQt5Core.so      -> libQt5Core.so.5.15.19
lrwxrwxrwx  libQt5Core.so.5    -> libQt5Core.so.5.15.19     ← 加载器要的就是这个名字
lrwxrwxrwx  libQt5Core.so.5.15 -> libQt5Core.so.5.15.19
-rwxrwx---  libQt5Core.so.5.15.19                           ← 真实文件
```

## 最小复现（决定性，20 行，自包含不依赖 Qt）

```bash
CLANG=/data/service/hnp/bin/clang
cat > libprobe.c <<'EOF'
int probe_answer(void) { return 42; }
EOF
cat > main.c <<'EOF'
#include <stdio.h>
extern int probe_answer(void);
int main(void) { printf("answer=%d\n", probe_answer()); return 0; }
EOF
$CLANG -shared -fPIC -Wl,-soname,libprobe.so.1 -o libprobe.so.1.0 libprobe.c
$CLANG -o main main.c -L. -l:libprobe.so.1.0          # NEEDED = libprobe.so.1

# 场景 A：libprobe.so.1 为**符号链接** → 真实文件
mkdir A && cp libprobe.so.1.0 A/ && ln -sf libprobe.so.1.0 A/libprobe.so.1
env LD_LIBRARY_PATH="$PWD/A" ./main; echo "A_EXIT=$?"

# 场景 B：libprobe.so.1 为**真实文件副本**
mkdir B && cp libprobe.so.1.0 B/libprobe.so.1
env LD_LIBRARY_PATH="$PWD/B" ./main; echo "B_EXIT=$?"
```

实测输出（本机）：

| 场景 | 目录内容 | stdout / stderr | 退出码 |
|---|---|---|---|
| **A** | `libprobe.so.1` = 符号链接 → `libprobe.so.1.0` | `Error loading shared library libprobe.so.1: (needed by ./main)` + `Error relocating ./main: probe_answer: symbol not found` | **127** |
| **B** | `libprobe.so.1` = 真实文件副本 | `answer=42` | **0** |

两个场景**仅"符号链接 vs 真实文件"一项不同** → 变量已隔离，归因成立。

## 影响范围

- 所有在 OHOS 上**以 conan 包目录为 `LD_LIBRARY_PATH` 直接运行动态链接产物**的场景：
  L2 冒烟门禁的 `bin/<exe> --version`、运行期手工验证、打包后自检。
- **构建期不受影响**：qmake/moc/uic/rcc 静态链接 Qt（NEEDED 仅 `libc++_shared`/`libc`）；
  编译链接阶段由 clang 按路径解析，不经加载器。
- conan 打包一律把 `<lib>.so.5.15.19`（真实）+ `<lib>.so{,.5,.5.15}`（符号链接）一起放入包，
  所以**任何**以包目录为库路径运行的动态产物都会命中，与具体软件无关。

## 推荐方案

按 **DT_NEEDED 传递闭包**遍历，把命中的库 **解引用复制**（`cp -L`）到可写临时目录，
再用该目录作为 `LD_LIBRARY_PATH` 重试。**两条排除是实测必需**：

```bash
for name in $(readelf -d "$item" | sed -n 's/.*(NEEDED).*\[\(.*\)\].*/\1/p'); do
    path=$(find_in_ldpaths "$name")   || continue
    case "$path" in
        /system/*|/vendor/*|/lib/*|/lib64/*|/usr/lib/*) continue ;;   # ① 系统库目录
    esac
    [ -e "$dest/$name" ] || cp -L "$path" "$dest/$name"               # -L = 解引用
    queue="$queue $dest/$name"                                       # ② 继续展开其依赖
done
```

1. **排除系统库目录**：`LD_LIBRARY_PATH` 常含 `/system/lib64`，整批搬运会把系统库也复制进来，
   `timeout`/`bash` 等系统程序自身加载失败（退出 127）。
2. **绝不复制 `/system/lib64/libc.so`**：会破坏 musl 的 libc 绑定（同样 127）。
   系统库一律交由系统自行解析。

真实效果（yasw）：直连 **127** → 解引用后 **124**（`timeout` 终止 = 已进入 Qt 事件循环）；
且 `yasw-consumer-runtime-relocated.log` 可见 Qt 真的初始化了
（`QStandardPaths: XDG_RUNTIME_DIR not set…`、`QFontDatabase: Cannot find font directory…`）。

## 与 `DRAFT-E5xx-registry-so-baked-absolute-needed-symlink` 的区别（勿混用）

| 维度 | E5xx（绝对路径烙印） | 本条（版本化符号链接） |
|---|---|---|
| `DT_NEEDED` 内容 | **绝对路径**（发布机缓存路径） | **soname**（`libfoo.so.5`） |
| 失败原因 | 该绝对路径在本机不存在 | 名字存在（是符号链接）但加载器不解析 |
| 解法 | 在**烙印路径处建 symlink** 指向真实库 | 把符号链接**解引用为真实文件**再喂给加载器 |
| 方向 | 造 symlink | **去** symlink |

判别方法：`readelf -d <exe> | grep NEEDED` —— 条目以 `/` 开头 → E5xx；是裸 soname → 本条。

## 禁止

1. **不要**把整个 `LD_LIBRARY_PATH` 无条件复制到临时目录（会引入系统库副本 → 127）。
2. **不要**用 `patchelf` 改写 soname/needed/rpath —— OHOS 对共享库有完整性/签名校验，
   改写后的副本可能被拒（`Permission denied`）。
3. **不要**因为退出码 127 就把运行期用例标为"跳过" —— 这是**可修复的环境限制**，
   127 是唯一能证明"GUI 真的起来了"的运行期证据来源。
