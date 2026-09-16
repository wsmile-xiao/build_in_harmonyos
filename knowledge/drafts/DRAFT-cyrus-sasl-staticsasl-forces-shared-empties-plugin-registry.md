# DRAFT-cyrus-sasl-staticsasl-forces-shared-empties-plugin-registry — `--with-staticsasl` 强制共享构建，静态插件注册表消失

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-13
> **Severity**: 🔴 high (blocking) | **Category**: build-system / autotools / plugin-registration / runtime

## 症状

`test_package` 断言「`auxprop_plugin='sql'` 可被解析」，CI 结果：

```
FAIL: auxprop_plugin 'sql' resolves to the SQL plugin (sasl_auxprop_store -> SASL_OK)
  ok   negative control: unregistered auxprop_plugin is rejected (SASL_FAIL)
```

## ★ 判别特征：正向失败 + 阴性对照"通过" ⇒ 注册表整体为空

这是本条最有价值的部分。看到这个组合时，**不要**去查"插件名是不是拼错"：

* auxprop 列表**整体为空**时，任何名字都查不到
* 于是「未注册名被拒」这句也"成立"，**阴性对照失去区分力** —— 它不再证明任何东西

换句话说，阴性对照本应证明"查找逻辑是有效的"，但在列表为空时它恒真。
正确解读是：**注册表是空的**，问题在"插件根本没被注册"，而非"名字不匹配"。

> 通用化：任何"断言某扩展/插件已被注册"的检查，若**正向失败而阴性对照反而通过**，
> 首先怀疑注册表为空，而不是名字或匹配大小写。

## 根因

两层叠加，缺一不成：

### ① `--with-staticsasl` 会**无条件**把 `enable_shared` 置为 yes

`configure.ac:104-107`：

```sh
AC_ARG_WITH(staticsasl)
if test "$with_staticsasl" = yes; then
	enable_shared=yes      # ← 即使命令行显式传了 --disable-shared
	enable_static=yes
fi
```

所以传 `--disable-shared --enable-static --with-staticsasl` 的配方，**最终仍会构建共享库**：
包内同时存在 `libsasl2.a` 与 `libsasl2.so`，而消费者（含 `test_package` 经 CMakeDeps）
默认链接到 **`.so`**。

### ② 共享构建下静态插件注册表不参与编译

`enable_shared=yes` 触发 `configure.ac:978-980`：

```sh
if test "$enable_shared" = yes; then
	AC_DEFINE(DO_DLOPEN,[],[Should we build a shared plugin (via dlopen) library?])
fi
```

而 `dlopen.c:432-459` 的静态注册表循环被 `#ifndef PIC` 包住：

```c
#ifndef PIC
    /* do all the static plugins first */
    for(cur_ep = entrypoints; cur_ep->entryname; cur_ep++) {
        ...
        for (p=_sasl_static_plugins; p->type; p++) {
            if(type == p->type)
                result = add_plugin(p->name, p->plug);
        }
    }
#endif /* !PIC */
```

→ **PIC 构建里这段根本不编译**，`.so` 中 `_sasl_static_plugins` 符号不存在。

`lib/staticopen.h:181-183` 里那个 SQL 注册项（`SPECIFIC_AUXPROP_PLUG_INIT( sql, "SQL" )`）
自然也没进 `.so`。于是 `.so` 只能经 **dlopen 从搜索路径**加载插件 ——
而未设 `SASL_PATH`（上游既有环境变量，`lib/common.c` 的 `SASL_PATH_ENV_VAR`）时
搜索路径为空 → **auxprop 列表为空**。

## 决定性证据（同一包里两个产物对比）

| 产物 | `_sasl_static_plugins` | 引用 `sql_auxprop_plug_init` |
|------|----------------------|---------------------------|
| `libsasl2.a` | **1** | **1** |
| `libsasl2.so.3.0.0` | **0** | **0** |

而 test 二进制的 `NEEDED`：

```
0x0000000000000001 (NEEDED)  Shared library: [libsasl2.so.3]
```

→ 消费者走的正是**没有注册表**的那份。

## 因果验证（同一二进制，只变环境变量）

| 条件 | 结果 |
|------|------|
| 不设 `SASL_PATH` | **8/9**（正向 FAIL，复现 CI） |
| `SASL_PATH=<pkg>/lib/sasl2` | **9/9 全过** |

## 修法

`package_info()` 里按编译期插件目录导出 `SASL_PATH`：

```python
self.runenv_info.append_path(
    "SASL_PATH", os.path.join(self.package_folder, "lib", "sasl2"))
```

这样消费者在 `conanrun` 环境下就能 dlopen 到随包交付的插件。
实测修复后完整 `conan create` **rc=0，9/9**。

## 禁止的两种"修法"

**❌ 让 `test_package` 改链 `libsasl2.a`**

`.so` 是消费者（CMakeDeps/pkg-config）**默认**拿到的产物。让测试改链 `.a` 只是让
测试通过，真实下游 SASL 使用者仍会因缺 `SASL_PATH` 拿到空插件表 ——
**问题被掩盖而非解决**，且丢掉了"共享构建需导出搜索路径"这条对消费者有意义的约定。

**❌ 去掉 `--with-staticsasl` 以为就不构建 `.so` 了**

实测去掉后 `configure` **rc=1**（该选项参与其它必要的静态配置路径）；
即便成功也改变了包交付形态。真正的修法是导出搜索路径，而不是翻转构建形态。

## 排查流程

```sh
# ① 判别：正向失败而阴性对照"通过" ⇒ 注册表整体为空
# ② 确认消费者实际链接 .so 还是 .a
readelf -d <test_binary> | grep NEEDED          # 期望 libsasl2.so.3
# ③ 对比两份产物的静态注册表符号
nm <pkg>/lib/libsasl2.a        | grep _sasl_static_plugins   # 有
nm <pkg>/lib/libsasl2.so.3.0.0 | grep _sasl_static_plugins   # 无
# ④ 因果确认：只变环境变量重跑
LD_LIBRARY_PATH=<pkg>/lib <test_binary>                          # 8/9（复现）
SASL_PATH=<pkg>/lib/sasl2 LD_LIBRARY_PATH=<pkg>/lib <test_binary> # 9/9（修复）
```

## 适用范围

凡是「**可选共享构建 + 静态插件注册表**」的 C/autotools 项目都可能同构 ——
判断时看注册表是否被 `#ifndef PIC`（或 `BUILD_SHARED` 一类）宏包住。

* 本条的 `SASL_PATH` 是 cyrus-sasl 的插件搜索变量；同类项目各有自己的
  搜索环境变量（如 `GIO_EXTRA_MODULES` 一类），需按项目对应处理
* 消费者侧典型是 `test_package` 或任何经 CMakeDeps/pkg-config 取包的下游

## 为什么本地手工验证会漏掉

该失败**只在 CI（走完整 `conan create` → test_package）暴露**，手工命令行构建
往往不暴露 —— 因为手工跑时环境里可能恰好有可用搜索路径，或干脆直接链了 `.a`。

**建议**：R34 验证一律走包级 `test_package`，不要用"手工跑一遍"替代 ——
手工验证跳过「真实消费者链接路径」，正是这类问题逃逸的缝隙。

## 诚实标注（limitations）

1. 结论基于 **cyrus-sasl 2.1.28** 源码与实测；上游若改写了
   `AC_ARG_WITH(staticsasl)` 的 `enable_shared` 赋值，需重新确认。
2. 「`.a` 有注册表 / `.so` 没有」是**静态与共享链接在插件发现机制上的固有差异**，
   不是 cyrus-sasl 独有缺陷。
3. 修法（导出 `SASL_PATH`）假定消费者确实需要 `.so`；若某下游明确只用静态库，
   链 `.a` 也能工作，但那不属于**包级默认约定**的问题。

## 相关

* `DRAFT-autotools-toolchain-vars-empty-vs-unset` —— 同属「autotools 配置语义
  与直觉不符导致的构建/测试失败」，但那条是 **shell 变量 `${VAR-default}` 语义**
  （空串不回退），本条是 **configure 选项覆盖命令行 + 宏条件编译**，根因不同
* E518（CI worker `git-clone` 缺 `libz.so`）—— 同一轮 CI 的另一个独立 worker
  环境问题，与本条无关
