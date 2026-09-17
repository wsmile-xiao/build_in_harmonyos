# libcidr 1.2.3 适配笔记

## 编译环境

- 构建系统: makefile（原生 BSD/GNU Makefile，无 configure / CMake / meson）
- 编译日期: 2026-09-15
- 编译器: clang（真机 `/data/service/hnp` 工具链，经 HMBS 预检实测）
- 状态: built（首轮仅完成未提交工作树，待真机预检回填实测结论）

## 上游信息

- 上游仓库: https://www.over-yonder.net/~fullermd/projects/libcidr
- 上游版本: 1.2.3（当前 release，tarball `libcidr-1.2.3.tar.xz`）
- 源码包: `https://www.over-yonder.net/~fullermd/projects/libcidr/libcidr-1.2.3.tar.xz`
- sha256: `afbe266a9839775a21091b0e44daaf890a46ea4c2d3f5126b3048d82b9bfbbc4`（2026-09-15 下载 tarball 实测，与 Debian `libcidr_1.2.3.orig.tar.xz` 一致，155144 字节）
- 许可证: BSD-2-Clause（LICENSE，另含 tools/lorder 的 FreeBSD 许可）
- 依赖: 无（零运行时依赖；W0 检查天然满足）

## 上游测试审计（结论：存在 perl 回归套件，以 python 复刻全量执行）

- 顶层 `Makefile` / `GNUmakefile`：目标仅 `all/build/clean/allclean/install/...`，无 `check/test` 目标。
- `src/Makefile`：目标仅 `all/build`（构建 `libcidr.so.0`），无测试目标。
- `src/test/Makefile`：`SUBDIRS = compare inaddr kids mkstr netbc nums parent`，`all/clean` 仅遍历构建 7 个手动验证程序，无 `check/test` 目标；7 个程序均为交互式演示（命令行取网段并打印比较/转换结果，`exit(0)`，无 PASS/FAIL 断言）。
- `src/test/regression/`：`test.pl`（perl5）+ `arr.pl`（期望表）为唯一自动化套件，仅覆盖 `mkstr`（`cidr_from_str`/`cidr_to_str`），`arr.pl` 含 114 个 `{'args','res'}` 向量；`test.pl` 经 `../run.sh ./cidr_mkstr -_ <args> <input>` 执行并比对 `'input' -> 'output'`。
- 源码树无 `tests/` 独立目录外的 gtest（无 `TEST(`/`TEST_F`）、ctest、pytest 痕迹；`find -name '*test*'` 仅命中 `src/test/` 演示与回归脚本。
- OHOS 工人未必提供 `perl5`，配方以 python 复刻 `test.pl` 逻辑（解析 `arr.pl` 全部向量，直调 `cidr_mkstr -_` 并比对），属低成本补齐；因此 `test_package/MANIFEST.yml` 记 `upstream_tests_exist: true`，`build()` 输出 `HMBS_UPSTREAM_TEST_RESULT(status=passed/framework=perl-regression/discovered=114)`，失败即构建失败。

## 编译步骤

```bash
make -j1 CC=<conan clang> LORDER=echo TSORT=cat -C .
make -j1 CC=<conan clang> LORDER=echo TSORT=cat -C src/test
# 回归（配方内 python 复刻 perl test.pl）：
#   LD_LIBRARY_PATH=src src/test/mkstr/cidr_mkstr -_ <args> <input> x114
```

> `LORDER=echo TSORT=cat` 用于绕过上游 `tools/lorder`（见下表 #6）：`GNUmakefile.inc`
> 以 `` `${LORDER} ${SO_FILES} | ${TSORT}` `` 决定共享库链接对象列表，OHOS
> 工具链下该脚本恒为空展开；`echo | cat` 直接回吐全量对象列表（共享链接与
> 静态归档不同，对象顺序无关）。
> CI #47997 证明这还不够（见下表 #7）：配方在 make 之后以 `_relink_shared_lib()`
> 用 CC 直编直链重建 `src/libcidr.so.0` 并以 `llvm-nm -D` 自检导出符号，测试程序
> 按 SONAME 动态解析，替换 .so 后无需重链即可验证。

产物拷贝（`package()`，不用 `make install`，保证布局确定性并规避设备缺 `install(1)`/软链接限制）：

- `include/libcidr.h` → `include/`
- `LICENSE` → `licenses/`
- shared：`src/libcidr.so.0` → `lib/` + 拷贝别名 `lib/libcidr.so`
- static（默认）：`src/*.So` 归档为 `src/libcidr.a` → `lib/`
- `src/examples/cidrcalc/cidrcalc` → `bin/`（chmod + binary-sign-tool 签名）
- `docs/libcidr.3` → `share/man/man3/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 顶层 `make install` 依赖 `install -c`、`mkdir -pm`、`ln -fs`，OHOS 设备缺 `install(1)` 且部分文件系统不支持软链接 | 上游面向 BSD/POSIX 发行版 | `package()` 手动 `copy()` 产物，`.so` 别名以文件拷贝交付，不调用 `make install` |
| 2 | 上游仅构建共享库，无静态目标 | 上游发布策略 | static 变体在 `build()` 末尾以 `llvm-ar rcs libcidr.a src/*.So` 归档 PIC 对象；`.So` 为 `ld -r` 可重定位对象，可直接归档 |
| 3 | 回归脚本需 `perl5`，OHOS 工人未保证提供 | 上游开发期脚本 | 以 python 复刻 `test.pl`（正则解析 `arr.pl`，`subprocess` 直调 `cidr_mkstr -_`），114 向量全量执行；`test.pl` 本体不动，不打补丁 |
| 4 | 构建树 ELF（`libcidr.so.0`、7 个 `cidr_*`、`cidrcalc`）在 OHOS 上直接执行可能因缺码签名失败 | OHOS 要求 ELF 签名 | 构建后以 `/data/service/hnp/bin/binary-sign-tool` 尽力签名（不存在则跳过），`cidrcalc` 在 `package()` 再次签名 |
| 5 | `conan_toolchain.cmake` 可能内嵌陈旧 `CMAKE_C_COMPILER=/data/service/hnp/bin/clang` | 预检工具链路径迁移 | test_package 复用 `libcli` 验证过的解析逻辑：PATH 查可用 clang/clang++，先替换 toolchain 文件中的陈旧路径，再以 `-DCMAKE_C_COMPILER/CXX_COMPILER` 覆盖配置 |
| 6 | CI #47983：`src/GNUmakefile.inc` 经 `` `../tools/lorder … \| tsort` `` 链接，OHOS（toybox sed/join）下脚本报错（`sed: _symbol_…`、`join` 用法错误）致对象列表空展开，`clang -shared` 产出零符号 `libcidr.so.0`，回归 0/114（`cidr_from_str: symbol not found`） | BSD `lorder` 依赖 BSD sed/join/nm 语义，与 OHOS 工具链不兼容；且 lorder 排序只对静态归档有意义，共享链接不需要 | make 命令行覆盖 `LORDER=echo TSORT=cat`（`?=` 允许覆盖并传递给子 make），`echo … \| cat` 直接回吐全量 `.So` 列表；无补丁，行为在真机/CI 双环境确定一致 |
| 7 | CI #47997：`LORDER=echo` 已生效（链接行含全部 10 个 `.So`）但 CI 仍 0/114、且 `binary-sign-tool` 唯独拒签 `libcidr.so.0`（其余 8 个 ELF 均签过），而同配方真机 114/114 | 上游 `.c.So` 规则的 `ld -r` 中间对象和/或 `clang -shared -Wl,-x` 在不同 worker 镜像行为不一致；lorder 只是第一病因 | 配方新增 `_relink_shared_lib()`：以 CC 直编 10 个源码为 PIC 对象、`CC -shared -Wl,-soname` 直链 `src/.relink/libcidr.so.0`（不用 `-x`/不用 `ld`），以 `llvm-nm -D` 验 `cidr_from_str/cidr_to_str/cidr_free` 确实导出（含 1 个上游 `.So` 抽查以区分 `ld -r` 与链接步骤），再拷贝覆盖 `src/libcidr.so.0` 并以实体文件落实 `libcidr.so` 别名；静态包改归档这批自检对象，不再用 `.So` |

## 源码修改

无补丁（`conandata.yml patches: {}`）。`CFLAGS` 未覆盖，保留上游 `-g -O2 -std=c99 -D_XOPEN_SOURCE=600` 及警告组（`-Werror` 已注释，不会因警告失败）。

## 依赖版本

无运行时依赖；构建仅需 C 编译器与归档器（由真机工具链经 Conan conf 提供）。

## 验证结果

```bash
# 待 HMBS 真机预检回填（conan create 全量日志）：
# - 上游测试标记：HMBS_UPSTREAM_TEST_RESULT(status=passed, framework=perl-regression, discovered=114, executed=114)
# - 消费者测试：test_libcidr 14/14（见 test_package/test_libcidr.c CHECK 清单）
```

test_package 覆盖（`test_libcidr.c`，14 个 CHECK，全部经真实 libcidr API）：

1. `cidr_from_str("192.168.1.0/24")` 返回非空
2. `cidr_get_pflen() == 24`
3. `cidr_to_str()` 回显 `192.168.1.0/24`
4. 超网/子网/无关网段解析均非空
5. `cidr_contains(192.168.0.0/16, 192.168.1.0/24) == 0`（包含）
6. `cidr_equals()` 对相同网段为真
7. `cidr_equals()` 对不同网段为假
8. IPv6：`cidr_from_str("::1/128")` 非空且 `CIDR_IPV6`
9. IPv6：`cidr_to_str()` 非空
10. `cidr_addr_network("192.168.1.77/24")` 得 `192.168.1.0/24`
11. `cidr_addr_broadcast()` 得 `192.168.1.255/24`
12. `cidr_from_inaddr()` 非空
13. `cidr_to_inaddr()` IPv4 往返一致
14. `cidr_version()` 非空

## 交付物

| 文件 | 说明 |
|------|------|
| include/libcidr.h | 唯一公开头文件 |
| lib/libcidr.a（默认）/ lib/libcidr.so.0 + libcidr.so（shared） | 静态 / 共享库（链接名 `-lcidr`） |
| bin/cidrcalc | 上游示例网段计算器 |
| licenses/LICENSE | BSD-2-Clause 许可证文本 |
| share/man/man3/libcidr.3 | 手册页（sed 生成） |

## 注意事项

- 链接名是 `-lcidr` 而非 `-llibcidr`（产物 `libcidr.so` 按惯例去 `lib` 前缀）；`package_info()` 已设 `cpp_info.libs=["cidr"]`，test_package 经 `find_package(libcidr)` / `libcidr::libcidr` 消费。
- 本库非系统同名库（R26 不适用），默认 static（`shared=False`）。
- 本轮严禁 commit/push；以上验证结论待真机 evidence 轮实测后回填，不得作为已验证引用。
