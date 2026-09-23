# cgicc 3.2.19 — Makefile 硬编码 `-lstdc++` 导致 OHOS 链接失败

## 问题

OHOS 工具链（clang 15 / aarch64-unknown-linux-ohos）只提供 libc++，不提供 libstdc++。
上游 autotools C++ 项目的 `Makefile.am`/`Makefile.in` 若在 `lib*_la_LDFLAGS` 硬编码
`-lstdc++`（libtool 链接阶段），报：

```
ld.lld: error: unable to find library -lstdc++
clang-15: error: linker command failed with exit code 1
```

## 根因

- cgicc 3.2.19 的 `cgicc/Makefile.am` 第 19 行硬编码 `libcgicc_la_LDFLAGS = -lstdc++ -version-info 5:10:2`
- OHOS SDK 工具链链接器为 lld，标准 C++ 运行库为 `libc++` / `libc++abi`（无 libstdc++）
- 与 E455（Conan profile `compiler.libcxx=libstdc++11` 注入 `-stdlib=libstdc++`）机制不同：
  这里是**上游构建文件硬编码**，需打补丁而非改 profile

## 方案

将 `Makefile.am`（源头）与 `Makefile.in`（tarball 模板）中 `-lstdc++` 改为 `-lc++`，
并用 `config.status` 重新生成 `Makefile`（不手改生成文件）：

```bash
# cgicc/Makefile.am 与 cgicc/Makefile.in
-libcgicc_la_LDFLAGS = -lstdc++  -version-info 5:10:2
+libcgicc_la_LDFLAGS = -lc++  -version-info 5:10:2
# 重新生成 Makefile（若已 configure）
./config.status cgicc/Makefile
```

## 验证

- `make -j2` 链接阶段通过（libtool 自动追加 `-lc++ -lc++abi`，本次人工 `-lc++` 无副作用）
- `conan-verify cgicc 3.2.19` G2 conan create 通过
- W3 本地 CI（build_and_test.sh）Pass rate 100% (1/1)

## 适用边界

- 仅适用于 OHOS/HarmonyOS PC 工具链（clang + lld + libc++）
- 适用于硬编码 `-lstdc++` 的 autotools C++ 库/程序的 `Makefile.am`/`Makefile.in`
- 若错误为 `-stdlib=libstdc++`（Conan profile 层）→ 属 E455，改 profile 而非补丁
- 若错误为 `unable to find library -lc++`（反向）→ 属 E191（工具链自身 libc++ 不可见）

## 反例 / 限制

- CI 干净环境下同样的 configure 会因 PATH 不同而表现不同，但链接错误与 PATH 无关
- 不能仅改 `Makefile`（生成文件），否则干净构建重跑 configure 后会回归；
  必须改 `.am` + `.in` 并重新生成

## 关键命令记录

- 链接错误复现：`make -j2`（cgicc/Makefile 链接 libcgicc.la 时 ld.lld 报错）
- 修复后验证：`make -j2` → `conan create` → `CI_PACKAGES="archives/c/cgicc/3.2.19" ci/conan/build_and_test.sh`