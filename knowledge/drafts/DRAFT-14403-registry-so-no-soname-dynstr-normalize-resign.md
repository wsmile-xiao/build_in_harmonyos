# DRAFT-14403-registry-so-no-soname-dynstr-normalize-resign

## 现象

kf5wayland 5.116.0 打包后 W3/CI L5b 门禁 fail：

```
[fail] L5b: libKF5WaylandClient.so 的 DT_NEEDED 含绝对/相对路径:
            /storage/Users/currentUser/.conan2/p/expat9fb72708ad085/p/lib/libexpat.so
L5_RESULT=fail: soname_gate_failed
```

readelf 实测：expat 包 .so **无 DT_SONAME 条目**（其余依赖 Qt6*/KF5Core 均正常）；
kf5wayland 两 .so 各有 ~16 个未定义 `XML_*` 符号（直接引用 expat，`--as-needed`
剔不掉）。

## 根因

expat 包 .so 无 DT_SONAME → 链接器把链接期的缓存绝对路径原样记为下游
DT_NEEDED。后果双重：①CI L5b 门禁 fail（非阻塞但难看）；②跨机/跨用户消费者
的 conan 缓存路径不同，按绝对路径解析 libexpat.so **必败**（运行时隐患，比门禁
更严重）。

## 修复

conanfile `package()` 内（签名**前**）新增 `_normalize_dyn_needed_paths`：

1. **字节级原位补丁**：扫描 .so 中所有 NUL 结尾字符串，将"以 `/` 开头且
   basename 匹配 `lib*.so(\.N)*`"的字符串原位替换为 basename + NUL 补零
   ——**同长度**（73→73 字节），DT_NEEDED 的 dynamic section 偏移不变、
   结构不动，仅 .dynstr 内容变化；
2. **重签**：objcopy 去旧 .codesign + binary-sign-tool 重签（生态惯例，
   qtbase/wayland 包 .so 均带 .codesign）；
3. **验证**：readelf -d 全按名（`NEEDED libexpat.so`）+ test_package 真实
   dlopen 加载并构造对象（5 断言全过）——证明补丁后重签的 .so 可被 OHOS
   平台正常加载。

## 验证

- 修复前：L5b fail（2 errors）+ 跨机消费者必败
- 修复后：L5b 清零（L5_RESULT=pass）、readelf `NEEDED libexpat.so`、
  test_package 5 断言全过（kf5wayland/5.116.0 PR #13869 实测）
- 与 cv14 打包产物基线对照：除 expat 绝对路径→库名外零差异

## 与 DRAFT-E5xx（symlink 方案）的分工

| | 本方案（归一化+重签） | DRAFT-E5xx（烙印路径 symlink） |
|---|---|---|
| 前提 | 可重签 + 可同长度补丁 | 文件内容不可变（不可重签） |
| 手段 | .dynstr 原位 basename 化 | 烙印绝对路径处 ln -s 真实库 |
| 产物 | 干净（按名解析，通用可移植） | 依赖烙印路径存在（HOME 树内） |

长期正解：expat 配方补 SONAME 重发布（依赖层修复，超出下游 PR 范围）。

## 适用范围

所有直接链接"无 SONAME 仓内包"（实例 expat）的下游配方；任何
"DT_NEEDED 烙印绝对路径 + 本包可控重签"的场景。
