# DRAFT: OHOS 动态加载器拒载未签名共享库（Permission denied）

> 状态：草稿（DRAFT）。待人工审核后 `graph promote` 为正式条目。
> 首发实证：libgexiv2 0.14.6（Meson 工程，OHOS aarch64 本机原生构建）。

## 现象

`conan create` 的 test_package 阶段，消费者二进制执行失败：

（以下为改名前的真实报错原文，当时包名为 gexiv2）

```
gexiv2/0.14.6 (test package): RUN: /data/service/hnp/bin/bash -c "./test_gexiv2"
Error loading shared library libgexiv2.so.2: (needed by ./test_gexiv2)
Error relocating ./test_gexiv2: gexiv2_get_version: symbol not found
ERROR: gexiv2/0.14.6 (test package): ConanException: Error 127 while executing
```

关键迷惑点：**同一份库在构建目录里能跑**——配方 `build()` 内的
`meson test -v` 上游回归套件 16/16 全部通过，只有 test_package 加载失败。

## 根因

| 事实 | 证据 |
|---|---|
| 未签名的 `.so` 被加载器拒绝，错误是 **`Permission denied`**（不是 `No such file`），极易误判为路径问题 | `LD_LIBRARY_PATH=<pkg>/lib python3 -c "import ctypes; ctypes.CDLL('libgexiv2.so.2')"` → `OSError: Error loading shared library ...: Permission denied` |
| 构建目录件可加载、install 件不可加载，**两份产物字节级仅 ~230 字节差异**（`.dynamic` 的 `DT_RUNPATH`/`.codesign`） | `md5sum` 不同 → `readelf -dW` 对比：构建件 31 项含 `RUNPATH`，install 件 30 项无 `RUNPATH`；`cmp -l` 差异仅 2 个 4K 页 |
| 因果确认：把 RUNPATH 字符串**清空**（条目保留）后同样复现 EACCES；换成带 RUNPATH 的那份内容即恢复 | 字节补丁实验（`d[i]=0` 于 RPATH 字符串首字节） |
| 用 `binary-sign-tool sign -selfSign 1` 原地签名后即可加载 | `sign` → `add codesign section success` → 加载成功 |
| test_package 自编译的测试二进制未签名时**内核 exec 门禁**直接抛 SIGTRAP | `Signal 5 (core dumped)` / exit 133 |

**为什么构建目录件能跑**：meson 构建件带 build rpath（指向依赖目录）且未被签名工具处理；`
meson install` 会**重链接**以剥离 build rpath，落地件因此既失去 rpath、又未获得
合法签名 —— 于 Linux 侧完全无害（LD_LIBRARY_PATH 仍可解析依赖），在 OHOS 侧则触发
签名门禁。这就是"本地 meson 全绿、conan test_package 却挂"的成因。

## 修复

```python
# conanfile.py package()：OHOS 分支对安装后的 ELF 统一自签名
if self.settings.os == "OHOS":
    self._create_shared_lib_aliases(os.path.join(self.package_folder, "lib"))
    self._sign_installed_elfs()

def _sign_installed_elfs(self):
    signer = "/data/service/hnp/bin/binary-sign-tool"
    targets = []
    for directory in ("lib", "bin"):
        root = os.path.join(self.package_folder, directory)
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            path = os.path.join(root, name)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            with open(path, "rb") as fh:
                if fh.read(4) != b"\x7fELF":
                    continue
            targets.append(path)
    for path in targets:
        self.run(shlex.join([signer, "sign", "-inFile", path,
                             "-outFile", path, "-selfSign", "1"]))
```

```python
# test_package/conanfile.py build()：测试二进制同样签名
self.run(shlex.join([signer, "sign", "-inFile", binary,
                     "-outFile", binary, "-selfSign", "1"]))
```

配套：`_create_shared_lib_aliases()` 把 `libgexiv2.so.2` / `libgexiv2.so` 这两个
soname 从符号链接落成**真实文件副本**（HMDFS 上 symlink 的 soname 解析不可靠）。

## 判据与最小验证

- **判据**：dlopen 报 `Permission denied`（而非 `not found`）→ 指向签名问题，
  而不是 `LD_LIBRARY_PATH`/路径问题。
- **最小验证**（不依赖 test 框架）：

```bash
LD_LIBRARY_PATH=<pkg>/lib python3 -c "import ctypes; ctypes.CDLL('libgexiv2.so.2')"
# 未签名 → OSError: Error loading shared library ...: Permission denied
# 已签名 → 正常返回
```

## 适用范围与先例

适用于**任何在 OHOS 上产出共享库、且运行时会被 dlopen/执行**的 Conan 配方；
对 Meson 工程尤其必然（`meson install` 一定重链接剥离 build rpath）。
仓库内同款先例：`archives/g/gdk-pixbuf/2.44.6`（`_sign_installed_elfs` 与
`_create_shared_lib_aliases`）；更早的 ELF exec 门禁大量实证见
`archives/a/ada-bar-codes/005` 的 `binary-sign-tool` 注释（1591 个配方在用该工具）。

## 边界与反例

- 非 OHOS 平台不适用（无该门禁，无需签名）。
- 签名后仍报 `Permission denied` 时，再查文件 mode（应含 `o+x`）、目录搜索权限、
  `LD_LIBRARY_PATH` 顺序；注意 HMDFS 上 `chmod` 可能不生效，不要指望用 `chmod` 修。
- 只签名「安装后的产物」不够：test_package 自编译的二进制也必须签，否则 SIGTRAP。
