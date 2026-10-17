# liborigin 3.0.4 适配笔记

## 编译环境

- 构建系统：CMake（上游最低版本 3.16.3，设备与 CI 工具链均为 CMake 4.1.2）
- 编译日期：2026-09-17
- 目标编译器：OHOS Clang 15.0.4（profile `ci/conan/profiles/ohos-aarch64`，C++17，libc++）
- 目标设备：aarch64 OHOS（HarmonyOS PC）
- 状态：built

## 源码

- 官方源：<https://github.com/gerlachs/liborigin/archive/refs/tags/3.0.4.tar.gz>
  （`gerlachs/liborigin` 为上游唯一开发仓库；savannah nongnu 的 liborigin 项目页
  已无发布文件——其下载路径 302 到镜像后返回 404）。
- SHA-256：`4e8a3d4fe298a9a4264f86b060a6dbd248dd8fe7c28b81bb88e739c1be8c78e1`
- 校验方式：设备 curl 直连 GitHub 与 codeload 镜像各下载一次，哈希一致；
  `init-build` 下载副本哈希相同。

## 编译步骤

1. `init-build` 取源并建立 orig/work 双轨（tar 校验通过）。
2. 原生探索构建：`cmake -DCMAKE_SYSTEM_NAME=OHOS -DGENERATE_CODE_FOR_LOG=1
   -DCMAKE_DISABLE_FIND_PACKAGE_Doxygen=ON ..` + `make -j2`，产物
   `liborigin.a`、`liborigin.so.3.0.4`（软链 .so.3/.so）、`opj2dat`。
3. 运行上游回归脚本（见下），在工作树上完成两处必要修改后用
   `refresh-patch --auto` 生成 5 个补丁。
4. `conan create`（私有 CONAN_HOME，profile `ohos-aarch64`）：
   默认静态 flavor 与 `-o shared=True` 共享 flavor 均通过，含 test_package 实跑。

## 关键适配点

### 1. os=OHOS 下的平台名与共享库 SONAME（核心）

Conan 的 CMakeToolchain 把 `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，
而 OHOS SDK 的 CMake 只提供 `Modules/Platform/OHOS.cmake`（内容一行
`include(Platform/Linux)`），没有 `Platform/HarmonyOS.cmake`。名字对不上时 CMake
不报错、只打印 "System is unknown to cmake" 继续，平台变量留空，其中
`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 为空 → 共享库无 `DT_SONAME`、不生成版本软链。

本配方按归档 `fmt 11.1.3` 的做法显式设置
`tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"`
（并设 `cmake_system_processor=aarch64`，避免为 unknown）。设备实测：
`liborigin.so.3.0.4` / `.so.3` / `.so` 三件齐全，`DT_SONAME=liborigin.so.3`，
消费方 `ld.lld` 按 SONAME 寻址正常。**走平台名对齐而非像同类配方那样手写
`-Wl,-soname,liborigin.so`，产物保持上游的版本化 soname 约定。**

### 2. 静态/动态二选一（上游默认两者都开）

上游 `BUILD_SHARED_LIBS`、`BUILD_STATIC_LIBS` 默认都为 ON，两个目标同名安装；
`opj2dat` 按 `if (BUILD_STATIC_LIBS) ... elseif (BUILD_SHARED_LIBS)` 选链接对象。
配方把 Conan `shared` 选项映射为二者互斥，默认静态：
- 静态（默认）：`lib/liborigin.a`，`bin/opj2dat` 自带实现，独立可运行（实测）。
- `-o shared=True`：`lib/liborigin.so.3.0.4`（+软链），消费方按 Conan 惯例经
  runenv 提供库路径；该 flavor 下 `opj2dat` 需要运行环境才能定位 `liborigin.so.3`
  （Conan 共享包的常规行为，未硬编码 RPATH）。

### 3. OHOS ELF 签名与安装期重写

OHOS 要求 ELF 携带有效 `.codesign` 才能执行/加载。CMake 安装阶段会清除可执行
文件的构建期 RUNPATH（构建树里 `opj2dat` 有绝对 RUNPATH，包内为空），字节一变
`.codesign` 即失效。首轮（尚未加入签名步骤时）实测：包内共享版 `bin/opj2dat`
直接执行被系统拒绝（`Operation not permitted`，rc=126，非缺库的 127）。受控复现
（取包内产物去掉 `.codesign` 段、保留可执行位）复得同类拒绝
（`Permission denied`，rc=126）；执行
`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`
重新自签名后立即可执行（rc=0）。配方因此在 `package()` 对包内 `bin/`、`lib/` 下的
真实 ELF（跳过版本化 `.so` 软链）统一重新签名——与归档 `fmt 11.1.3` 同一做法。

签名发生在安装之后，故包内 `lib/liborigin.so.3.0.4` 与构建树同名产物字节不同
（签名段内容不同，属预期行为）；签名后的库与 CLI 实测加载/执行正常：静态 flavor
的 `bin/opj2dat` 无额外环境即可运行，共享 flavor 经 Conan runenv 提供库路径后运行
（未硬编码 RPATH）。证据：`logs/…-codesign-eperm-repro2/output.txt`、
`logs/…-final-rev-shared-verify/output.txt`。

### 4. 公共 API 链接修复（patch 0001）

`OriginFile.h:65` 声明 `liboriginVersionBugfix()`，`OriginFile.cpp:291` 却定义
`liboriginVersionPatch()`，且库内无任何调用者。test_package（首个真实消费方）
按头文件调用时报：

```
ld.lld: error: undefined symbol: liboriginVersionBugfix()
```

补丁把定义改名为头文件声明的名字，返回值不变（`LIBORIGIN_VERSION_PATCH`）。
上游 master 仍存在该不一致（2026-09-17 核对）。

### 5. 上游回归夹具版本横幅（patch 0002–0005）

`tests/examples/*.out.orig` 是上游 `tests/run-example-import-tests.sh` 的期望输出。
3.0.4 标签内的这 4 个文件首行仍是 `opj2dat 3.0.3, ...`，而脚本对整份 stdout 做
`diff -u`，因此直接跑必然 FAIL。上游随后在 master 上自行修复了同一问题：

- 提交 `2ab0436` "tests: fix version in reference output"（2026-07-28），
  4 个文件各改 1 行。

补丁与上游修复内容一致（只改版本横幅）。夹具本身由上游 `compile` 脚本的
`-DGENERATE_CODE_FOR_LOG=1` 构建设定生成：开启日志时 opj2dat 才打印
`Project has N windows.` 与工程树，因此本任务的上游测试复现按该设定构建。

### 6. 其他

- `CMAKE_DISABLE_FIND_PACKAGE_Doxygen=ON`：避免命中 Doxygen 时 `doc ALL` 目标进入
  构建（构建机是否装 doxygen 会改变构建内容）。
- `CMAKE_INSTALL_LIBDIR=lib`：防止 64 位 GNUInstallDirs 落到 `lib64` 而
  `cpp_info.libdirs` 仍按 `lib` 解析。
- 删除上游安装的 `lib/pkgconfig/liborigin.pc`：其 `prefix` 内嵌 configure 期路径，
  改为 `pkg_config_name=liborigin` 由 Conan（PkgConfigDeps）生成等价元数据。
- 头文件安装在 `include/liborigin/`，`cpp_info.includedirs` 与之对齐
  （与上游 `.pc` 的 `Cflags: -I${includedir}/liborigin` 一致），消费方写
  `#include <OriginFile.h>`。
- 命令声明：产物含 `bin/opj2dat`，软件级 `commands.json` 已按 R38 声明。

### 7. 工具链行为说明（非本包缺陷，如实披露）

- finish 的 G0「干净构建验证」（step 3/10）对 CMake 项目仍按 `./configure` 探测，
  liborigin 无该脚本，该步报 `./configure: No such file or directory`（rc 0 之外的
  框架提示）；官方 SKILL 标注该步非阻塞，实际构建由 `conan create`（G2）与 W3
  本地 CI 完整验证并全部通过（见 reports/）。
- CI 的 L2 smoke 探针使用 `--version`/`--help`，而上游 `opj2dat` 的版本开关是 `-v`
  （无长选项），探针落到 CI 设计内的非阻塞提示分支；CLI 实际可运行性由本任务
  实测覆盖（`-v` rc=0、`--check-only` 与完整导出均与上游参考一致）。

## 上游测试清点（R51）

上游测试入口为 `tests/run-example-import-tests.sh`（bash，856 字节），对
`tests/examples/*.opj` 逐个运行 `opj2dat` 并比对：

| 夹具 | OUTPUT 比对（stdout vs `.out.orig`） | DATA 比对（`.1.dat` vs `.1.dat.orig`） |
| --- | --- | --- |
| `2folder-with-graphs.opj`（9.85，4 数据集/2 工作簿/2 图形） | 有 | 有 |
| `crash.opj`（9.3，746 数据集/1 Excel） | 有 | 无（上游未提供） |
| `data+graph-7.0.opj`（7.0，2 数据集/1 工作簿/1 图形） | 有 | 有 |
| `reciprocal-scale-x.opj`（9.95，2 数据集/1 工作簿） | 有 | 有 |

清点口径：上游用例 = 4 个 `.opj` 样例（脚本主循环单元），每个样例包含 1 项 OUTPUT
比对与（有参考文件的）1 项 DATA 比对，共 7 项断言。

实跑（设备原生，aarch64 OHOS，clang 15.0.4，`GENERATE_CODE_FOR_LOG=1` 构建）：

```
Testing 2folder-with-graphs.opj ...  OUTPUT PASS / DATA PASS
Testing crash.opj            ...  OUTPUT PASS
Testing data+graph-7.0.opj   ...  OUTPUT PASS / DATA PASS
Testing reciprocal-scale-x.opj ...  OUTPUT PASS / DATA PASS
退出码 0
```

即 4/4 用例通过（7/7 比对逐字节一致）。

### 补丁前后对照（证明 patch 0002–0005 是唯一差异来源）

打补丁前用同一构建实测：3 项 DATA 比对逐字节一致，4 项 OUTPUT 比对仅首行
版本横幅不同（其余逐字节一致）。同步横幅后全部 PASS。该差异属上游 tag 内
夹具滞后，与平台适配无关。

## 消费者测试（test_package）

`test_package/test_liborigin.cpp` 链接安装后的 `liborigin::liborigin`，读取随
test_package 携带的上游夹具。夹具是上游样例 `tests/examples/data+graph-7.0.opj`
的 base64 文本（`fixtures/data+graph-7.0.opj.b64`，二进制文件不进源码仓），
`test_package/conanfile.py` 在构建/测试时解码为 24329 字节的 `.opj` 并校验
SHA-256 `9bd6b300066d6a8d62e1078a6893e8d34d860955cdb7adf20be973f35a36a99b`
（与上游 tag 内原件逐字节一致）。消费者程序共 **22 项断言**：

- 版本 API：`liboriginVersionString()=="3.0.4"`、major/minor/bugfix、数值编码。
- 解析：`parse()` 成功、工程版本 7.0、spread/dataset/graph/matrix/excel/function/note
  计数、`project()` 非空。
- 结构：工作簿名 `Data1`、2 列、`maxRows==30`、列名 A/B、列类型 X/Y。
- 数据：前 4 行 (1,2)/(2,4)/(3,5)/(4,6) 与上游参考一致；第 5–30 行为 `_ONAN`
  缺测标记；`dataset(0)` 与工作簿 A 列一致。

实测（`conan create`，静态与 `-o shared=True` 两种 flavor 各一轮）：
`TEST_PACKAGE_OK (22 checks)`，退出码 0。

## 验证结果

| 项目 | 结果 |
| --- | --- |
| 上游回归脚本（设备原生，7 项比对） | PASS（4/4 用例，退出码 0） |
| `conan create` 默认（静态） | PASS（test_package 22/22） |
| `conan create -o shared=True` | PASS（test_package 22/22） |
| 包内 `bin/opj2dat` 实跑（静态 flavor，无额外环境） | PASS（`-v` rc=0；导出 `.1.dat` 321 字节，内容与上游参考一致） |
| 共享库 SONAME / 版本软链 | PASS（`DT_SONAME=liborigin.so.3`，三件齐全） |
| 包内 ELF 签名 | PASS（bin/、lib/ 下 ELF 均含 `.codesign`，重签后可执行） |
| 补丁按序应用（5/5） | PASS（`apply_conandata_patches` 于 conan create 中实际生效） |

## 交付物

| 文件 | 说明 |
| --- | --- |
| `lib/liborigin.a`（默认）或 `lib/liborigin.so.3.0.4`（`-o shared=True`） | 解析库 |
| `include/liborigin/*.h`、`tree.hh` | 公共头文件（4 个） |
| `bin/opj2dat` | `.opj` → `.dat` 导出工具（软件级 `commands.json` 声明） |
| `licenses/COPYING` | GPL-3.0 许可证文本 |

---

**编译结束**：2026-09-17

**最终状态**：built
