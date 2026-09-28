# 可重定位的 PG 扩展：产物落包内 + 集群参数指回去；PG 18 的 `$libdir` 简单名剥离让 control 无需改写

> DRAFT-pgroonga-4.0.8-pg-extension-relocatable-install-and-discovery
> （知识库扩展草稿，路径 B）与 pgroonga 4.0.8 归档同 PR 交付。

一个 PostgreSQL 扩展要交付三样东西：`.control`、`<name>--<ver>.sql`、以及一个
或多个 `.so`。在普通主机上它们分别装进 `sharedir/extension` 与 `pkglibdir`，
一切顺理成章。在 Conan 里，这两个「理所当然的目的地」都不存在——而 PG 又只会
去固定的几个地方找它们。

## 两个约束

**(a) 不能往 PG 安装目录写。** Conan 打的 postgresql 是 DESTDIR 可重定位安装，
编译期前缀为空，没有稳定的 `pkglibdir` / `sharedir` 可写；而且那个目录属于
**依赖包**，往依赖包目录写文件既被只读 cache 挡住，也会破坏包指纹。

**(b) PG 只去固定几处找扩展。**

| 找什么 | 去哪找 |
|--------|--------|
| `.control` 与版本 SQL | `<sharedir>/extension` |
| 共享库 | `pkglibdir`，以及 `$libdir` 展开后的路径 / `dynamic_library_path` |

产物既然在别处，就必须在**运行期**把这两处搜索路径指过去。

## 构建期：落点

关掉「装进 PG 目录」，并把扩展脚本目录显式钉死：

```python
tc.project_options["install_to_postgresql"] = False
tc.project_options["datadir"] = "share"
```

第二条别省。`MesonToolchain` 默认会把 `datadir` 设成 `resdirs[0]`，很容易得到
**`share/res/extension`** —— 目录结构看着挺像对的，PG 却永远不会去那里找。
`autotools` / `cmake` 的等价做法是显式传 `--datadir=<pkg>/share`。

产物布局应当是：

```
<pkg>/lib/pgroonga.so
<pkg>/share/extension/pgroonga.control
<pkg>/share/extension/pgroonga--4.0.8.sql
```

## 运行期：把搜索路径指回去

```
extension_control_path = '<pkg>/share/extension:<pg>/share/postgresql/extension'
dynamic_library_path   = '<pkg>/lib:<pg>/lib/postgresql:$libdir'
```

### 坑一：`extension_control_path` 是**替换**不是追加

PG 自带的 `<pg>/share/postgresql/extension` **必须保留**在列表里。
`plpgsql.control` 就在那，而 `initdb` 会在模板库里建 plpgsql。只写本包那一段，
症状是**集群起不来**，报错还是「找不到 plpgsql」这种跟你的扩展八竿子打不着
的信息。

`dynamic_library_path` 里的 `$libdir` 同理要保留，让 PG 自己的模块
（`plpgsql.so` 等）仍能被解析。

### 坑二：control 文件**不用**改

自然的疑问是：`pgroonga.control` 里写着

```
module_pathname = '$libdir/pgroonga'
```

而这份 PG 的编译期前缀为空，`$libdir` 展开出来是坏路径——是不是要给 control
打个补丁？

**不用。** PG 18 的 `load_external_function` 对「简单名」——`$libdir/` 之后再
不出现目录分隔符——会**剥掉 `$libdir/` 前缀**，把裸名交给 `dynamic_library_path`
搜索，再依次尝试 `name` 与 `name + DLSUFFIX`。所以只要
`dynamic_library_path` 里含 `<pkg>/lib`，`$libdir/pgroonga` 就能解析到
`<pkg>/lib/pgroonga.so`。

（反过来说：如果 `module_pathname` 写成 `$libdir/pgxs/pgroonga` 这种带子目录的
形式，就不再是「简单名」，剥前缀逻辑不适用——那时才需要另想办法。）

所以本包**不带任何补丁**。这本身是一条可验证的结论，值得在 test_package 里
钉成断言：

```sql
-- 必须仍有 $libdir/pgroonga 形式的 probin
SELECT count(*) FROM pg_proc WHERE probin = '$libdir/pgroonga';   -- > 0
-- 且不得出现任何含绝对路径的 probin（构建机/安装机路径烘进 catalog 就是坏了）
SELECT count(*) FROM pg_proc WHERE probin LIKE '/%'
                                OR probin LIKE '%/%/%';           -- = 0
```

外加一条**反向断言**：`<pg>/lib/postgresql/<name>.so` 与
`<pg>/share/postgresql/extension/<name>.control` 都必须**不存在**。这条断言
证明产物落点确实是本包、确实靠搜索路径被发现，而不是走了"偷偷装进 PG 目录"
那条不可重定位的捷径。

## 反模式

- **把 `module_pathname` 的 `$libdir/<name>` 改写成绝对路径**：等于把当前机器
  的路径烘进 catalog。同一条 control 一旦被搬到别的路径就失效，绝对路径还会
  通过 `pg_dump` 扩散到下游。而且这是**不必要**的——简单名剥离已经让原样
  写法可用。
- **往依赖包的 `package_folder` 里写产物**：Conan cache 只读，且写入不改变包
  指纹，跨 worker 会得到"有时改过有时没改"的不确定状态。
- **只设 `extension_control_path` 不保留 PG 自带那段**：见「坑一」。

## 适用范围

同样的形状出现在任何「宿主只从固定目录加载插件、而插件由另一个 Conan 包提供」
的地方：GStreamer 插件（`GST_PLUGIN_PATH`）、GLib GIO modules
（`GIO_EXTRA_MODULES`）、PAM modules。区别只是宿主对应的开关名不同——但
「产物落包内 + 运行期指回去 + 不碰宿主安装目录」这三步是一致的。

## 相关

- `DRAFT-pgroonga-4.0.8-conan-postgresql-empty-prefix-pg-config-shim`
  —— 解决「**构建时**怎么找到 PG」（pg_config 回坏路径）；
  本篇解决「**运行时** PG 怎么找到扩展」。两者是同一件事的两端。
- `DRAFT-pgroonga-4.0.8-pg-regress-without-ruby-on-live-tcp-cluster`
  —— 扩展装好之后，怎么把这个可重定位的 PG 跑起来并驱动上游回归。
