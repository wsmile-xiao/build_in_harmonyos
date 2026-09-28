# 依赖包烘焙的构建机前缀有两副面孔：`*.pc`（配置期，重生成）与共享库里的资源目录（运行期，环境变量覆盖）

> DRAFT-pgroonga-4.0.8-groonga-dep-baked-build-prefix-pc-and-plugins-dir
> （知识库扩展草稿，路径 B）与 pgroonga 4.0.8 归档同 PR 交付。

pgroonga 自己不复杂，它把复杂度都放在依赖上：检索引擎 Groonga 以
`dependency('groonga', version: '>= 14.1.0')` 的形式进来。Groonga 由本仓库的
`groonga/16.0.8` 提供，而这份包在两个完全不同的时机、以两种完全不同的形式
把**构建机路径**泄漏给了消费者。

## 面孔一：`*.pc` 里的 `prefix=`（配置期）

依赖包里的 `groonga.pc` 长这样：

```
prefix=/storage/Users/currentUser/.conan2/p/b/groonf04c74dc6be8e/p
libdir=${prefix}/lib
includedir=${prefix}/include
Name: groonga
Version: 16.0.8
Libs: -L${libdir} -lgroonga
Cflags: -I${includedir}
```

`prefix` 是**构建机上那个临时目录**（Conan 的 `p/…/p` 中间目录），不是设备上
解包后的最终路径。于是 `pkg-config --cflags groonga` / `--libs groonga` 给出的
`-I` / `-L` 全指向不存在的目录：

- 乐观情况：`dependency('groonga')` 直接 `Package 'groonga' not found`；
- 悲观情况：找到了（因为在构建机上恰好还能访问），编过、链过，**装到设备上才
  出问题**——而这时的报错与 pkg-config 毫无关系。

注意这不是「Conan 没做好重定位」：`.pc` 这份**文本**是在构建机上生成的，
写死了当时的 prefix。Conan 包的二进制是重定位的，`.pc` 不是。

**修法**：让 Conan 按**当前包目录**重新生成一份。

```python
generators = "PkgConfigDeps"
```

`PkgConfigDeps` 会为所有依赖生成 `<name>.pc`（`groonga.pc`、`msgpack-c.pc`、
`libxxhash.pc`…），`MesonToolchain` 自动把 generators 目录追加进
`pkg_config_path`；CMakeToolchain 与 autotools 同理——把 generators 目录放进
`PKG_CONFIG_PATH`。于是上游拿到的 `-I` / `-L` 指向真实目录，而版本约束
（`>= 14.1.0`）用的仍是真版本号。

> **反模式**：把依赖包里的 `groonga.pc` 原样拷进 `PKG_CONFIG_PATH`。那份
> `.pc` 的 prefix 就是问题本身，拷过去等于什么都没修，只是把「路径不存在」
> 从 Conan cache 搬到 build 目录。

## 面孔二：`.so` 里固化的资源目录（运行期）

Groonga 有一个插件机制：tokenizer、token filter、query expander 等都是
`lib/groonga/plugins/` 下按目录分类的共享对象，由 `libgroonga.so` 在运行时
`dlopen`。而「插件目录在哪」是**编译期固化**进二进制的：

```
$ strings libgroonga.so | grep -i 'groonga/plugins'
/storage/Users/currentUser/.conan2/p/b/groonf04c74dc6be8e/p/lib/groonga/plugins
```

同样是那个构建机临时目录。后果很有迷惑性：

- `libgroonga.so` 能正常 `dlopen`，全文检索、索引、查询语法**全部正常工作**；
- 只有当某个用例用到**插件**时才报错，而且是 Groonga 自己的措辞：
  `unsupported tokenizer` / `unsupported token_filter`。

「大部分功能都好，个别功能报 unsupported」这个症状，与「构建/打包错误」的
直觉完全不搭，很容易误判成"那个功能本来就不支持"或"插件没编进去"。

**修法**：运行期用 `GRN_PLUGINS_DIR` 覆盖。

```python
def _groonga_plugins_dir(self, libdirs):
    for d in libdirs:                       # 沿依赖图收集到的所有 libdir
        cand = os.path.join(d, "groonga", "plugins")
        if os.path.isdir(cand):
            return cand
    return None

env["GRN_PLUGINS_DIR"] = plugins_dir        # test_package / conanrun
```

不写死包名、走依赖图递归收集，依赖增删都自动跟上。

> **反模式**：拿 `LD_LIBRARY_PATH` / `LD_PRELOAD` 去「让 groonga 找到插件」。
> 它们只影响**库能不能被找到**，不影响**库去哪找它的插件**。混淆这两件事，
> 排查会卡在「库明明加载成功了，为什么还 unsupported」。

## 顺带一条：`feature(auto)` 不能留给运气

上游把可选特性做成 Meson 的 `feature` 且默认 `auto`：

```
option('message_pack', type: 'feature', value: 'auto')
option('xxhash',       type: 'feature', value: 'auto')
```

`auto` 意味着「探测到就启用」，而探测结果**是环境相关的**。同一份配方在不同
worker 上可能一份 enabled、一份 disabled，且构建期不报错——直到运行期出现
符号缺失。

做法是两头都钉死：

```python
def requirements(self):
    self.requires("msgpack/7.0.1")     # 显式依赖
    self.requires("libxxhash/0.8.3")

def generate(self):
    tc.project_options["message_pack"] = "enabled"   # 与依赖一致
    tc.project_options["xxhash"] = "enabled"
```

## 判定信号

```bash
grep -H '^prefix=' "$DEP_PKG"/lib/pkgconfig/*.pc        # 指到 p/…/p 构建机路径?
strings "$DEP_PKG/lib/libgroonga.so" | grep -i plugins  # 固化的是构建机路径?
```

两条任一命中 → 配置期用生成器重生成 `.pc`，运行期用环境变量覆盖资源目录。
**不要试图只修一半**：这两副面孔分别出现在配置期和运行期，修了 `.pc` 不会
让插件目录变得可用。

## 相关

- `DRAFT-pgroonga-4.0.8-conan-postgresql-empty-prefix-pg-config-shim`
  —— 同样是「依赖包里带着构建机/空前缀」，但那是 `pg_config` 这类**配置工具**
  的输出，修法是塞 shim，与前两条都不同。
