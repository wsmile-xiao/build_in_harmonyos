# DRAFT：bitcoin 系测试链双范式（boost test 自编 + MWEB bdb 桩头）

## 错误特征（可机器匹配）

```
cannot find -lboost_unit_test_framework
fatal error: 'db_cxx.h' file not found
```

## 根因

**范式一：测试链供给缺口**
bitcoin 系 0.21（末代 autotools 版本）的上游单元测试链硬依赖
libboost_unit_test_framework.a。制品仓 boost1.84 拆分包系无
boost1.84-test 件；boost/1.84.0 主包不含该库文件，但**带全量头文件**
（boost/test/ 全目录 + test/impl/*.ipp 实现 21 个齐全）——头在库不在。

**范式二：禁用模块的遗留传递包含链**
`--disable-wallet` 切断 BDB 的链接依赖，但 litecoin 特有 MWEB 模块
（libmw）的 Keychain.cpp 传递包含 wallet/scriptpubkeyman.h →
walletdb.h → bdb.h → db_cxx.h——头依赖链未断，编译期仍要求 BDB 头。
"禁用模块"只断链接不断包含，是 --disable-X 场景的通病。

## 修法

### 范式一：主包头文件自编静态库（零新增供给包）

```python
# conanfile build() 内
boost_pkg = self.dependencies["boost"].package_folder
ipp_dir = os.path.join(boost_pkg, "include", "boost", "test", "impl")
ipps = sorted(glob.glob(os.path.join(ipp_dir, "*.ipp")))  # 21 个
objs = []
for ipp in ipps:
    obj = ipp + ".o"
    self.run(f"{cxx} -c {ipp} -o {obj} -I{boost_pkg}/include "
             f"-DBOOST_TEST_NO_LIB -DBOOST_ALL_NO_LIB")
    objs.append(obj)
self.run(f'ar rcs "{build_dir}/libboost_unit_test_framework.a {" ".join(objs)}"')
# Makefile 链接段（configure 后注入 LDFLAGS/ LIBrary path）
```

20 个编译单元、约 2 分钟编译——比新增 boost1.84-test 供给包轻量一个
数量级，且随主包版本自动对齐。

### 范式二：最小桩头替代

bdb.h 的 `#include <db_cxx.h>` 替换为 `#include <db_cxx_stub.h>`：
桩头只含类声明（Db/DbEnv/DbTxn/Dbc/Dbt 五类 + 各自最小方法面）+
常用 DB_* 常量 + `typedef unsigned short __kernel_sa_family_t`。
**适用前提**：被禁用模块的产物不链接（无符号需求）——仅头解析通过。

## 与相邻条目边界

- DRAFT-boost184-component-pack：组件打包供给（拆包分发）——本条是
  消费端自编（零包），互补；
- E041/E059/E071：autotools 工具链故障——本条是依赖供给与头依赖；
- mydumper #2983 Find 模块范式：CMake Find 层——本条是 autotools
  链接层+包含链层。

## 案例

| 库 | 场景 | 验证 |
|---|---|---|
| litecoin 0.21.4 | 双范式全用 | test_litecoin 462/462（100%）双次真跑；CI #46309/#46915 绿 |
| bitcoin 31.1.1 | 范式一 CMake 变体 | Boost::unit_test_framework target（先例参考） |

## 推广面

- bitcoin 系全族（bitcoin/dogecoin/dash 等 0.2x autotools 系）
- 任何用 boost test 且仓无 -test 拆分件的 C++ 库
- 任何 --disable-X 后头依赖未断的库（桩头范式）
