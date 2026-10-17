# OHOS 动态加载器不解析符号链接形式的 DT_NEEDED

## 场景

libnm 1.52.1（NetworkManager 客户端库）适配到 OHOS aarch64，meson + Conan 2.29。
上游 meson 测试套件 54 项，其中 23 项在 `conan create` 的 `build()` 阶段直接 exit 127。

## 症状

```
Error loading shared library libgnutls.so.30: (needed by /path/build/src/libnm-core-impl/tests/test-crypto)
```

- **括号内是空的**——没有 `No such file or directory`，这是最容易误判的地方
- 进程 exit 127
- 文件明明就在 `LD_LIBRARY_PATH` 指向的目录里，`ls -l` 可见
- 同一批失败里出现的库名随用例不同：`libgnutls.so.30` / `libpsl.so.5` / `libtasn1.so.6` /
  `libgcrypt.so.20` / `libgpg-error.so.0` / `libidn2.so.0`

## 根因

**OHOS（musl）动态加载器拒绝解析符号链接形式的 `DT_NEEDED`。**

目标文件存在、可读、权限正确、路径也在搜索范围内，但它是符号链接 —— 加载器在 DT_NEEDED
查找阶段就放弃，并且 musl 在这一分支上打印的 strerror 是空字符串。

### 决定性对照实验（双对象最小探针）

用 OHOS clang 交叉编译一个"依赖任意共享库"的最小二进制，同一二进制 + 同一
`LD_LIBRARY_PATH`，只改依赖文件的形态：

| 依赖文件形态 | 运行结果 |
|---|---|
| 实体文件（`cp -L` 复制） | `rc=0`，探针返回值 `42`（符合预期） |
| 符号链接（`ln -sf` 指向实体） | `rc=127`，报 `Error loading shared library ...: (needed by ...)` |
| 改回实体文件 | `rc=0` |

三次往返稳定复现，排除了路径、权限、strerror 文案等干扰因素。

### 为什么仓库里的 glib / nss 包"看起来没问题"

仓库既有事实约定由此解释：`binary-sign-tool sign -inFile X -outFile X -selfSign 1` 是**原地签名**，
写入时会**解引用符号链接**变成实体文件。glib 包 20 个 `.so`、nss 包 10 个 `.so` 全部是实体、
零符号链接，正是因为其 `package()` 的签名 glob **不跳过 `islink`**。
反过来，签名循环里写 `if islink: continue` 就会把 soname 链原样（符号链接）交付出去。

## 修复

三处都要做，缺一不可：

### ① 产物侧 —— 签名循环不要跳过 islink

```python
for target in targets:
    if not os.path.exists(target):
        continue
    self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
    self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
```

原地签名顺带把 `libnm.so -> libnm.so.0 -> libnm.so.0.1.0` 全部实体化。
验证：三个文件 `islink=False`、字节完全一致（libnm 实测均 1882752 B，
sha256 `fdd8a9534476660eb59830a2c09c78afbb1f52178a6fd03ddf7b1901ca405380`）。

### ② 构建期测试侧 —— 私有运行时目录

依赖包 libdir 里的 soname 仍是符号链接，必须在 `build_folder` 下建一个实体化目录
（`shutil.copy2(os.path.realpath(src), ...)`），并**前置**到 `LD_LIBRARY_PATH`。

### ③ 消费端 test() 侧 —— 同上，且自己拼环境

`test_package` 里同样实体化，并**自行拼接 `LD_LIBRARY_PATH`**（实体化目录在前），
然后以 `env=None` 运行，不要叠加 `conanrun` 环境脚本（它的顺序会把依赖 libdir 排前面，
先命中符号链接就照样失败）。

**这三步只写 `build_folder`，不修改任何依赖包。**

## 验证

```
修复前：40/54 中的 23 项因 exit 127 失败
修复后：通过数 20/54 -> 40/54，剩余 14 项全部由沙箱环境（netlink/D-Bus/keyfile）导致
```

## 关键词

`Error loading shared library`, `needed by`, symlink, 符号链接, DT_NEEDED, SONAME,
exit 127, empty strerror, binary-sign-tool, selfSign, islink, materialize, 实体文件,
LD_LIBRARY_PATH

## 相关条目

- **E316**（Conan 包 SONAME 实体缺失 libopenblas.so.0）—— 同属"NEEDED 文件不可解析"家族，
  但 E316 是"文件没带上"，本条是"文件带上了但形态是符号链接"，误诊方向不同
- **E274**（package() 未创建版本化 SONAME 符号链接）—— 方向相反：本条要消灭符号链接
- **E073 / E207** —— 同类运行时加载失败
