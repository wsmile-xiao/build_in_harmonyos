# E580 — init-build F068 嵌套源码提升误判 autotools 项目（根目录仅 configure.ac）

## 错误特征

init-build 解压 tarball 后，work/orig 目录**只剩扁平文件**（对应业务子目录的内容），
而 configure.ac、Makefile.am、Db/、Main/、Parser/、Test/ 等真实源码目录全部消失。
日志中可见：
```
嵌套源码检测: 找到源码在 Server，正在提升到 whitedb-0.8.0alpha.work ...
嵌套源码提升完成: Server → whitedb-0.8.0alpha.work
```
（Server 为含手写 Makefile 的业务子目录）

## 触发条件

- 构建系统: autotools
- 阶段: init-build（源码解压后自动嵌套提升）
- 前提: tarball 根目录只有 configure.ac + Makefile.am（**无预生成 configure / Makefile**），
  且源码内含带手写 Makefile 的子目录（如 whitedb 的 `Server/`）

## 根因分析

`init_build.py` F068 的 `_promote_nested_source()` 用
`_BUILD_MARKERS = ("configure", "CMakeLists.txt", "Makefile", "meson.build")`
判断目录是否为源码根：

1. `_extract()` 的单层提升把 `whitedb-0.8.0alpha/` 提升到 dest 根目录——此步正确；
2. 根目录此时含 `configure.ac`/`Makefile.am`，但**不含** `_BUILD_MARKERS` 中的
   `configure` 或 `Makefile` → `_has_build_marker(root)` 返回 False；
3. `_find_source_subdir()` 递归搜索子目录，遇到含手写 `Makefile` 的 `Server/` 即返回；
4. `_promote_nested_source()` 把 `Server/` 提升到根目录，并**删除其余全部非点号前缀目录**
   （Db/Main/Parser/Test/Admin/Python 等）——真实源码树被整体摧毁。

根因本质：`_BUILD_MARKERS` 不识别 autotools 源码包的 `configure.ac`/`Makefile.am`
组合，导致对"根本无嵌套层级"的包触发二次误提升。

## 解决方案

### 推荐方案（manual-rebuild-dual-track）

判定 work/orig 只剩扁平文件后，从 tarball 重建双轨目录：

```bash
# 1. 备份损坏目录 → 重建 .orig（仅单层提升，不做嵌套提升）
mv .orig .orig.broken && mv .work .work.broken
mkdir -p .orig && tar xzf $BUILD_TARBALL -C .orig
sub=$(ls -d .orig/*/ | head -1); mv $sub/* .orig/ && rmdir $sub
sha256sum $BUILD_TARBALL | awk '{print $1}' > .orig/.tarball-sha256

# 2. 重建 .work + edit-tracker 基线
mkdir -p .work && cp -a .orig/. .work/ && rm -f .work/.tarball-sha256
python3 -c "from ohc.edit_tracker import snapshot; snapshot('.work')"

# 3. 清理损坏备份
rm -rf .orig.broken .work.broken
```

重建后用 `find . -name configure.ac`、`ls -d Db Main Test` 验证结构完整，
再继续 Step 2 编译（autoreconf → configure → make → make check）。

### 禁止做法
- ❌ 直接继续 make/configure——源码树不完整必然失败且难以定位
- ❌ 删除原始 tarball——它是唯一完整源码来源
- ❌ 只恢复某个子目录——其余真实源码目录（Db/Parser/Test）已被删除

## 验证证据

whitedb 0.8.0alpha（GitHub priitj/whitedb）实测：
- init-build 后 `.work` 仅 17 个扁平文件（Makefile/Manifest/dserve.c 等 Server/ 内容），
  与 tarball 内 `Server/` 目录 18 个文件对应；
- `configure.ac`、`Db/`、`Main/`、`Test/` 全部缺失；
- 手动重建后 `edit_tracker snapshot` 基线 243 个文件；
- autoreconf/configure/make/make check 全部通过（TOTAL=2 PASS=1 SKIP=1 FAIL=0）。

## 适用边界

- ✅ 适用：tarball 根目录仅 configure.ac/Makefile.am 的 autotools 项目
- ✅ 适用：源码内含手写 Makefile 子目录的项目
- ❌ 不适用：tarball 根目录已有预生成 configure/Makefile 的包（不会触发）
- ❌ 不适用：CMake/meson 项目（E195 已覆盖 src/ 提升场景）

## 与既有条目的关系

- **similar_to: E195**（init-build 嵌套源码提升丢失同级目录）
  - 重合点：同一函数 `_promote_nested_source`，都会删除非点号前缀同级目录
  - 差异点：E195 是 CMake 项目 `src/`（含 CMakeLists.txt）被正确识别后提升、误删
    同级 include/testcase；E580 是 autotools 项目根目录 `configure.ac/Makefile.am`
    不匹配 `_BUILD_MARKERS`，递归误判 `Server/`（手写 Makefile）提升、摧毁整树
  - 新增价值：揭示 `_BUILD_MARKERS` 对 autotools 源码包判定的盲区，扩展了
    受影响软件范围（此前仅 CMake 项目），给出双轨重建的完整命令
