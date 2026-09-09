# DRAFT-hoedown-3.0.7：test_package 共享库运行期解析失败（默认静态却打包 .so）

> Contributor: Tianyi Wang | Status: Draft | Updated: 2026-09-07
> Source: task hoedown-3.0.7-r01-bootstrap-and-adapt-pc2-33-20260906T143857Z
> （conan-verify G2 首次 conan create 失败链）

## 背景

hoedown 3.0.7 是纯 Makefile 库（无 configure），上游 `make all` 同时产出
`libhoedown.a`、`libhoedown.so.3`（+ `.so` 符号链接）以及 `hoedown`/`smartypants`
两个可执行文件。配方默认 `options.shared=False`（静态优先），但 package() 起初把
`.a` 与 `.so.3` 都装进包内，导致 `conan create` 的 test_package 阶段运行期失败。

## 错误：test_package 运行期报共享库加载失败

### 现象

```text
1/1 Test #1: test_hoedown .....................***Failed    0.02 sec
Error loading shared library libhoedown.so.3: (needed by .../test_hoedown)
Error relocating .../test_hoedown: hoedown_html_renderer_new: symbol not found
Error relocating .../test_hoedown: hoedown_document_new: symbol not found
...
ERROR: hoedown/3.0.7@ohpcd/stable (test package): Error in test() method
```

编译与链接阶段全部成功（CMake 找到 hoedown::hoedown 目标并链接），仅运行期失败。

### 根因

1. 链接器 `-lhoedown` 在 lib 目录同时存在 `libhoedown.a` 与 `libhoedown.so` 时
   默认**偏好共享库**，test 二进制带 `NEEDED libhoedown.so.3`。
2. ctest/conan runenv 未把包内 lib 目录加入 `LD_LIBRARY_PATH`（本机 musl 加载器
   不做 `$ORIGIN` 回退），运行期加载器找不到 `libhoedown.so.3`。
3. 依赖库整体未加载 → 其全部符号无法重定位 → 报一串 `Error relocating ... symbol not found`。

### 修复

`package()` 按 `self.options.shared` **条件打包**：静态默认只装 `.a`，shared 才装
`.so.3` + 符号链接。默认静态构建下 test_package 链接纯静态产物，运行期无共享库解析问题。

```python
if self.options.shared:
    copy(self, "libhoedown.so.3", self.source_folder, libdir)
    if not os.path.lexists(os.path.join(libdir, "libhoedown.so")):
        os.symlink("libhoedown.so.3", os.path.join(libdir, "libhoedown.so"))
else:
    copy(self, "libhoedown.a", self.source_folder, libdir)
```

### 验证

- 修复前：`conan create` test_package 阶段 ctest 1/1 Failed（如上现象）。
- 修复后：`conan create` 完整通过，test_package 1/1 Passed（test.c 调用
  hoedown API 渲染 Markdown 并断言 `<h1>`）；W3 本地 CI 模拟 L0-L5 全 pass。

## 查重差异（为何不与既有条目等价）

| 条目 | 差异 |
|------|------|
| E078 | "Error relocating.*symbol not found" 文字命中，但根因是 musl BIND_NOW 下 dlopen 的 Python/Perl 扩展模块链接参数；本条是普通 test 二进制 NEEDED 共享库未在加载路径 |
| E088 | "ImportError.*Error loading shared library" 文字命中，但场景是 Python dlopen 命名空间（fix=copy-to-$ORIGIN）；本条是 ctest 运行期 NEEDED 库、根因是配方同时打包两种产物 |
| E131/E135 | 分别为 .so Permission denied 与 libintl.so.8 特定缺失，非本模式 |

## 适用边界

- 纯 Makefile 型库（无 configure）、上游同时产出 .a 与 .so、配方默认静态。
- 对 CMake 型库同样适用（CMakeDeps 链接同样偏好 .so）。

## 反例 / 限制

- 若下游必须共享消费 hoedown（`-o shared=True`），静态默认不满足 → 必须提供
  shared 分支，本方案两种模式都自洽。
- 不要依赖给 conan runenv/LD_LIBRARY_PATH 打补丁来兜底：HarmonyOS musl 加载器
  对命名空间/RUNPATH 限制多，ctest 环境不注入包内 lib 目录，行为不可复现。
