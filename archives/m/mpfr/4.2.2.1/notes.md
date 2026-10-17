# mpfr 4.2.2.1 编译笔记（HarmonyOS PC · Conan autotools）

## 为什么另起 4.2.2.1

与 `mpfr/4.2.2` 的差异**只有一处**：`package()` 里装完后删掉 `lib/*.la`。
源码、补丁、configure 参数、依赖全部逐字不变。

### 4.2.2 的 .la 会让下游 libtool 链接失败

conan 按 `prefix=/` 构建，于是 4.2.2 装出的 `lib/libmpfr.la` 里写着：

```
dependency_libs=' -L<gmp libdir> //lib/libgmp.la'
```

那个 `//lib/libgmp.la` 根本不存在。下游只要用 libtool 链接、且 `-lmpfr`
命中了这个 `.la`，libtool 就会顺着 `dependency_libs` 递归解析并失败：

```
libtool: error: cannot find the library '//lib/libgmp.la' or unhandled argument '//lib/libgmp.la'
```

LinBox 1.7.0 实撞，链到 `liblinbox.la` 这一步直接停住。

### 试过但无效的绕行

把 LinBox 侧生成的 `libtool` 脚本里 `link_all_deplibs` 改成 `no`——**无效**。
已确认补丁确实写进了 `build-release/libtool`（`grep '^link_all_deplibs='` 得 `no`），
报错一字不变。原因是 libtool 在**解析 `-lmpfr` 命中的那个 `.la` 时**就展开
它的 `dependency_libs`，与「链接时要不要把 deplibs 也加进去」这个开关无关。

所以只能从源头解决：不装 `.la`。依赖的真实链接信息 conan 已通过 `.pc` 与
`cpp_info` 完整提供，`.la` 在 conan 体系里没有任何用处。

制品仓不支持同版本多 revision（R37），故按仓库 `.N` 惯例新增 4.2.2.1，
4.2.2 保持原样、现有下游不受影响。

## 真机验证（2026-08-12，HarmonyOS PC MateBook）

`conan create -pr ohos-native` 通过：

- **上游 `make check -j1`**：TOTAL 198 / PASS 195 / SKIP 3 / FAIL 0 / ERROR 0
  （与 4.2.2 记录的一致，证明删 `.la` 不影响构建与测试）
- **test_package**：ctest 1/1 通过，输出 `MPFR 4.2.2 result: 42.0`
- **产物核对**：`lib/` 下只有 `libmpfr.a` 与 `pkgconfig/`，`.la` 确已不存在

## 顺带发现：仓里还有其它包带同样的坏 .la

在设备的 conan cache 里普查 `//lib/` 烤死路径，除 mpfr 外还命中：

- `pcre2` 的 `libpcre2-posix.la`
- `libgcrypt` 的 `libgcrypt.la`
- `net-snmp` 的 `libnetsnmpagent.la` / `libnetsnmpmibs.la`

它们目前没挡住我这条依赖链，未单独处理；如果哪个下游用 libtool 链接到它们，
会撞上同样的问题，修法相同。
