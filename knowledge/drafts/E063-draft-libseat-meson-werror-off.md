# Meson + -Werror + OHOS SDK 头文件警告（E063 的 meson 变体草稿）

> 状态：草稿（DRAFT，待人工审核）｜来源：libseat 0.9.1 OHOS aarch64 适配（2026-09-07）｜similar_to: E063

## 问题

在 OHOS（HarmonyOS PC）交叉编译中使用 Meson 构建时，上游工程若开启
`default_options: ['werror=true']`，会被 **OHOS SDK 头文件自身的警告** 卡死：

```
sys/socket.h:360:44: warning: comparison of integers of different signedness ...
      expanded from macro 'CMSG_NXTHDR'
        __CMSG_LEN(cmsg) + sizeof(struct cmsghdr) >= __MHDR_END(mhdr) - (unsigned char *)(cmsg)
```

`-Werror` 把该警告升级为错误 → `conan create` 编译失败。问题根因在 SDK 头文件
宏展开（`__CMSG_LEN(...) + sizeof(...) >= __MHDR_END(...) - (unsigned char *)(...)`
混用有符号/无符号），**与目标库源码无关**。

## 根因

1. OHOS SDK `sys/socket.h` 的 `CMSG_NXTHDR` 宏存在有符号/无符号比较；
2. 上游 meson 工程 `werror=true` 将警告升级为错误；
3. 编译目标库时该头文件被间接包含（libseat 的 connection.c 通过 sys/socket.h）。

## 方案（配方式，无源码补丁）

在 conanfile.py 的 `generate()` 中，仅 OHOS 平台关闭 werror：

```python
def generate(self):
    tc = MesonToolchain(self)
    # ...
    if self.settings.os == "OHOS":
        tc.project_options["werror"] = "false"
    tc.generate()
```

与 E063（make/CFLAGS 系 `-Wno-error=...`）的差异：本条目面向 **Meson/MesonToolchain
native 配置注入路径**，通过 `project_options` 在 meson 配置层关闭，无需改 CFLAGS
或源码。同源先例：seatd/0.9.1 与 libseat/0.9.1 配方均采用此法并通过 G2 干净构建。

## 验证

- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` → G2 PASS
- 上游确定性测试（linked_list、connection）通过；消费者测试 16/16 断言通过

## 适用边界 / 反例

- 适用：Meson + werror=true + OHOS SDK 头文件警告的 C/C++ 库适配。
- 反例：警告源于**目标库自身代码**时不得关闭 werror 掩盖（应修源码，见 E063 路径）；
  非 meson 工程（autotools/make）请参考 E063 的 CFLAGS 方案。
- 关系：similar_to=E063；不冲突。

## 查重差异（七轴）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false |
| causal_duplicate | false（SDK 头文件宏 vs musl/clang 差异警告） |
| trigger_overlap | 部分（E063：同为 -Werror 升级） |
| solution_overlap | 部分（E063 用 CFLAGS；本条目用 meson project_options） |
| combination_novelty | true（meson + MesonToolchain + OHOS SDK 头文件警告 + werror 组合无覆盖） |
| boundary_novelty | true（meson native 配置注入路径为新边界） |
| test_migration_novelty | true（meson 系仓库标准配方选项） |
