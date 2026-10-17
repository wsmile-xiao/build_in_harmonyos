# DRAFT — init-build 嵌套源码检测误判：构建入口在 contrib/ 子目录的 header-only 库被删源码

> Status: DRAFT (contributor pc2-44) | Source: gemmlowp/0.8.7 adaptation, task gemmlowp-0.8.7-r01-pc2-44-20260926T172052Z
> Environment: HarmonyOS PC aarch64, OHOS SDK clang 15.0.4, Conan 2.29.1 (OHOS), init-build (F068 嵌套源码检测)

## 1. 问题现象

`ohc-run.py init-build gemmlowp 0.8.7 --url=<commit tarball>` 执行成功（exit 0），
但 `.orig`/`.work` 目录里真实源码全消失，只剩 contrib/ 提升上来的文件：

```
$ ls .orig/
.gitignore  .tarball-sha256  .travis.yml  CMakeLists.txt      # 只剩 4 个文件
$ ls .orig/contrib/   # 不存在——已被提升为源码根
```

真实 tarball 顶层应有：public/、fixedpoint/、internal/、meta/、eight_bit_int_gemm/、
test/、doc/、profiling/ 等源码目录（65 个 .h + 18 个 .cc）。

## 2. 根因

gemmlowp 根目录没有 init-build `_BUILD_MARKERS` 中的任何构建文件
（configure/CMakeLists.txt/Makefile/meson.build——官方构建系统是 Bazel：
根目录只有 BUILD + WORKSPACE），而 contrib/ 子目录存在
`contrib/CMakeLists.txt`（Debian 维护者编写的 CMake 构建入口）。

`init_build.py` 的 `_find_source_subdir` 递归找到 contrib/CMakeLists.txt（唯一构建
标记）→ `_promote_nested_source` 把 contrib/ 内容提升到源码根，并**删除所有非点号
开头的同级目录**（public/、fixedpoint/、internal/、meta/、eight_bit_int_gemm/、
test/、doc/ 等全部真实源码目录被 rmtree 删除），只保留 contrib/ 的三个文件
（CMakeLists.txt、.gitignore、.travis.yml）。

E195 已覆盖「src/ 子目录有构建文件 → 提升丢失同级目录」的**同机制**，但本条是新
触发面：E195 场景是根目录有 CMakeLists.txt（在 src/ 下引 ../include），gemmlowp 是
**根目录完全无构建标记 + 构建入口在 contrib/ 子目录**——`_find_source_subdir` 递归
深度可达 3 层，任何子目录里的构建文件都可能被误提升。

## 3. 判定与验证

| 检查 | 命令 | 结果 |
|---|---|---|
| 根目录构建标记 | `ls configure CMakeLists.txt Makefile meson.build` | 均不存在（Bazel：BUILD/WORKSPACE） |
| contrib 子目录 | `ls contrib/CMakeLists.txt` | 存在（Debian 编写） |
| 源码完整性 | `ls public fixedpoint internal meta test` | 提升后全消失 |
| tarball 顶层 | `tar tzf $BUILD_TARBALL | head` | 含 public/、fixedpoint/ 等真实目录 |
| SHA-256 校验 | `sha256sum $BUILD_TARBALL` | c3feb896a1b42595cf9a508ed64ed0dc3cd84fffdb8eed790d02d0534ab322ce |

处置：手动整树重建 `.orig`/`.work`（见 §4 命令），核对 `.tarball-sha256` 后继续主流程。

## 4. 修复（当前 task 内落地）

```bash
B=/storage/Users/currentUser/tmp/builds/gemmlowp-0.8.7
rm -rf $B.orig $B.work
mkdir -p $B.orig
tar xzf $B.tar.gz -C $B.orig --strip-components=1
echo "c3feb896a1b42595cf9a508ed64ed0dc3cd84fffdb8eed790d02d0534ab322ce" > $B.orig/.tarball-sha256
cp -a $B.orig $B.work
rm -f $B.work/.tarball-sha256
# 核对
ls $B.work/ | grep -E '^(public|fixedpoint|internal|meta|eight_bit_int_gemm|test)$'
```

## 5. 适用边界与反例

- **适用**：构建入口在非 src/ 子目录（contrib/、cmake/、build-aux/ 等）且根目录
  无任何被识别构建标记的库；尤其 header-only 库（头文件在根级目录）。
- **反例**：根目录确有 CMakeLists.txt/Makefile 的库不触发（`_has_build_marker` 先
  查根目录）；tarball 单层 wrapper 目录（`_extract` 已做单层提升）不算本条。
- 不得在被提升的残缺目录上继续编译（源码已缺，证据失真）；不得伪造
  `.tarball-sha256`（W3/finish 校验哈希一致性）。

## 6. 查重差异

- **E195**（restore-from-tarball，正式知识）：同机制（`_promote_nested_source` 删除
  同级目录）+ 同恢复方法（从 tarball 恢复），但 E195 error_signature 是
  `CMakeLists.txt: No such file or directory|../include.*not found`（src/ 提升后路径
  失效），本条签名是**根目录无构建标记 + 构建入口在 contrib/ + 整树源码被删**。
  → `trigger_overlap`（同工具同函数）+ `solution_overlap`（restore-from-tarball），
  `boundary_novelty`（contrib/ 触发面 + 整树删除，可跨库复用）。
- 四范围检索 "contrib / promote / 嵌套源码 / build_script_folder"：正式知识 0 命中
  （E195 为 src/ 场景；E217 是 header install 子目录，主题不同）。
- 新增差异：根目录无构建标记 + 子目录构建入口（contrib/ 类）→ init-build 误提升
  删源码，无既有条目覆盖该触发面。
- 关系：`similar_to=E195`，无 conflicts/caused_by。

## 7. 处置（对 gemmlowp 的落地）

1. init-build 后核对 .orig 目录结构，发现真实源码目录消失、只剩 contrib/ 提升内容；
2. 按 §4 整树重建 .orig/.work，核对 .tarball-sha256 = c3feb896...（与 tarball 一致）；
3. 关键目录（public/fixedpoint/internal/meta/eight_bit_int_gemm/test）齐全后继续
   lang-preflight → 编译 → conan → finish 主流程；
4. 本条记录为 init-build 工具缺陷（框架侧），不在软件 PR 内改框架。

## 禁止

- 禁止在被提升的残缺目录上直接编译或声称源码完整；
- 禁止伪造 .tarball-sha256；
- 禁止把误提升当作上游源码布局（gemmlowp 真实源码根是仓库根，contrib/ 只是 CMake 入口）。