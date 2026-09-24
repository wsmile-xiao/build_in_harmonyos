# E647-draft-libplist-2.6-dict-uint-api-backport-static-inline：libplist 2.6+ dict API 缺失时的 static inline backport 与 conanfile 版本门控（libimobiledevice-progs 1.4.0）

## 错误特征

```
ld.lld: error: undefined symbol: plist_dict_get_uint
>>> referenced by ideviceimagemounter.c
clang-15: error: linker command failed with exit code 1
tools/afcclient.c:379:59: error: use of undeclared identifier 'PLIST_OPT_NONE'
```

## 触发条件

- 适配对象调用 libplist 2.6.0 新增的 `plist_dict_get_uint()` /
  `plist_dict_copy_uint()`（libimobiledevice 1.4.0 的
  afcclient/idevicebackup2/idevicecrashreport/ideviceimagemounter 四个工具）
- 或使用 `PLIST_OPT_NONE` 枚举值（同为 2.6.0 新增，plain 0）
- 制品仓依赖图锁定 libplist/2.3.0：libimobiledevice/1.3.0、
  libimobiledevice-glue/1.3.0、libtatsu/1.0.5 都直接 `requires("libplist/2.3.0")`，
  任何同图包升 2.7.0 都会版本冲突

## 根因

libplist 2.6.0 起 dict helper 从宏/内联迁移为真正的导出函数并新增
`PLIST_OPT_NONE`；上游 libimobiledevice 1.4.0 工具源码已改用新 API，
而 registry 的 libplist/2.3.0 头文件与静态库里没有这些符号。

`plist_new_unix_date()`/`plist_set_unix_date_val()`（2.7.0 API）**不在**问题面：
上游用 `#ifdef HAVE_PLIST_UNIX_DATE` 门控，configure 的
`AC_CACHE_CHECK(for plist_new_unix_date)` 探测失败即走
`plist_set_date_val(node, time - MAC_EPOCH, 0)` 老路径。

## 解决方案（三件套）

1. **逐字 backport 头**：把 libplist 2.6.0 `src/plist.c` 中
   `plist_dict_get_uint`/`plist_dict_copy_uint` 的实现原样拷成
   `tools/plist_dict_compat.h` 的 `static inline`（LGPL-2.1+ 同许可），并在头内
   `#ifndef PLIST_OPT_NONE #define PLIST_OPT_NONE 0 #endif`。函数签名所需类型
   （`plist_err_t`、`PLIST_ERR_*`、`plist_new_uint`、`plist_get_string_ptr`、
   `plist_get_data_ptr`、`plist_get_node_type`）在 2.3.0 头里全部已存在（已核）。

2. **最小 include 门控**：只在 4 个调用文件的 `#include <plist/plist.h>` 后插

   ```c
   #ifdef LIBPLIST_LT_2_6
   #include "plist_dict_compat.h"
   #endif
   ```

   其余 5 个 2.6.0 helper（get_bool/copy_bool/copy_string/copy_data/copy_item）
   本源码树零调用，不 backport，保持最小面。

3. **conanfile 侧版本探测**（不 patch 4 万行生成版 configure）：

   ```python
   from conan.tools.scm import Version
   plist_version = str(self.dependencies["libplist"].ref.version)
   if Version(plist_version) < "2.6.0":
       env.append("CPPFLAGS", "-DLIBPLIST_LT_2_6=1")
   ```

   注意 Conan 2.29 的 `AutotoolsToolchain` **没有** `extra_cppflags` 属性，宏要经
   `Environment().append("CPPFLAGS", ...)` 随 build scope env 脚本注入。

registry 将来发布 libplist >= 2.6.0 后，门控自动关闭，compat 头不再编译，
真实库函数接管——包不需要再改。

## 取数命令（在被测源码树根执行）

```bash
# 调用面全集——不要 head 截断（本任务实测截断漏 idevicebackup2.c，多烧一轮构建）
grep -rln "plist_dict_get_uint\|plist_dict_copy_uint" tools/ common/ src/
# 其余 2.6.0 helper 是否被用（本树为零）
grep -rln "plist_dict_get_bool\|plist_dict_copy_bool\|plist_dict_copy_string\|plist_dict_copy_data\|plist_dict_copy_item" tools/ common/ src/
# 修复后自含性（libplist 应静态链入，NEEDED 只剩系统库/共享传递依赖）
readelf -d <package>/bin/ideviceinfo | grep NEEDED
```

## 禁止

- **不要**用 `head` 截断调用面枚举——漏一个文件就是再红一轮。
- **不要** patch 生成版 configure 来降 `LIBPLIST_VERSION` 门槛或注入宏：hunk
  上下文随上游 reconfigure 漂移（libtatsu/1.0.5 的 configure patch 属历史形态）。
- **不要**在依赖图里单方面升 libplist/2.7.0：glue/tatsu 的直接依赖仍是 2.3.0，
  conan2 会版本冲突；override 后家族包未经二进制验证。

## 类似条目

无直接同族条目；libtatsu/1.0.5 配方注释里的 7-helper backport 是本模式的库侧先例
（其门控在 configure，本条迁移到 conanfile 侧）。
