# GUI 应用编译期绝对数据路径（PKGDATADIR）在 OHOS conan 包内不可解析 → 应用内环境变量覆盖（默认回退）

**草稿条目**（`DRAFT-gnutrition-0.33-app-datadir-env-override`）
来源：gnutrition 0.33 Conan 适配（2026-09-27）。

## 现象

GTK3 GUI 应用 gnutrition 把数据目录编死成编译期宏 `GNUTRITION_DATADIR`
（= `$datadir/gnutrition`，conan `--prefix=/` 下成为 `//share/gnutrition`），
运行时直接 `snprintf("%s/food.db", GNUTRITION_DATADIR)` 拼绝对路径。
conan 包内数据实际落在 `<package_folder>/share/gnutrition`，不在 `/` 下：

```console
$ <pkg>/bin/gnutrition
gnutrition: cannot open database '//share/gnutrition/food.db': unable to open database file
```

## 根因（与库场景的差异）

同类触发在库上已有方案（E546 gupnp-av：`runenv_info.define_path` 注入消费者环境；
libint2 草稿：`cpp_info.defines` 传 DATADIR 编译期宏）——**但它们都依赖
"存在 cpp_info 消费者"这个注入点**。GUI/CLI **应用**没有库消费者，
没有 defines/runenv 可注入；修复只能在**应用源码内**完成：
`getenv()` 覆盖 + 空值回退编译期默认。configure `--prefix=/` 的 OHOS
conan 打包让路径变成 `//share/...`，使问题必然暴露。

## 推荐方案（应用内补丁，默认回退）

```c
static char food_db_full_path[1024];
const char *datadir = getenv ("GNUTRITION_DATADIR");
if (datadir == NULL || *datadir == '\0')
  datadir = GNUTRITION_DATADIR;
snprintf(food_db_full_path, sizeof(food_db_full_path), "%s/food.db", datadir);
db_path = food_db_full_path;
```

- 空值/未设置 → 回退编译期默认（不改变原生行为）；
- 测试/用户可指向 conan 包内 `share/gnutrition`；
- 与 OHOS headless 纪实分类配合（E471）：越过数据层后到 GTK 显示依赖边界。

## 验证（三用例运行探针，test_package/harmonyos_specific_test.c，3/3 PASS）

| 用例 | 环境 | 可观测结果 |
|---|---|---|
| A 有效目录 + broadway | `GNUTRITION_DATADIR=<pkg>/share/gnutrition` `GTK_BACKEND=broadway` | 无 "cannot open database"（sqlite3 数据层通过）；随后 Gtk-WARNING cannot open display（E471 显示依赖边界） |
| B 无效目录 | `GNUTRITION_DATADIR=/nonexistent` | 报错含 `/nonexistent/food.db`（覆盖生效） |
| C 未设置 | 无 | 报错含 `//share/gnutrition/food.db`（默认回退保持） |

## 适用边界

- 适用：带数据文件、用编译期 PKGDATADIR/DATADIR 宏 + 绝对路径拼接的应用（GTK/Qt/CLI），
  OHOS conan `--prefix=/` 打包场景必现；
- 反例：库场景应优先用 E546 `runenv_info.define_path` / libint2 `cpp_info.defines`
  （注入点存在时更稳，无需改上游源码）；
- 反例：可写前缀安装（DESTDIR 到真实 `/share`）时不需此补丁，但 OHOS 系统分区只读不可行。

## 查重差异（七轴摘要）

- trigger_overlap：E546/E6344/libint2 同类触发（编译期数据目录在 conan 包内断裂）；
- solution_overlap：部分 —— 库侧用 defines/runenv 注入；本候选为**应用侧 in-app getenv 补丁**，
  既有条目未覆盖此边界（无 cpp_info 注入点的应用）；
- boundary_novelty：应用边界 + 三用例（有效/无效/未设置）运行探针为可复用验证范式；
- 完整关系见归档 notes.md 的知识候选台账。