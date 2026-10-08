# AutotoolsToolchain.generate() 无参调用会丢弃 tc.environment() 的修改

> Draft: `DRAFT-CONAN-TOOLCHAIN-GENERATE-ENV-DROPPED-PKG-CONFIG-PATH`
> Stem: `conan-toolchain-generate-env-dropped-pkg-config-path` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-CONAN-TOOLCHAIN-GENERATE-ENV-DROPPED-PKG-CONFIG-PATH
- **严重度**: 2
- **类别**: conan|packaging|dependency-injection
- **触发工具**: conan
- **阶段**: packaging

## 错误特征

conan 2.x 配方里这样注入 PKG_CONFIG_PATH（R49 依赖注入模式）：

```python
tc = AutotoolsToolchain(self)
env = tc.environment()
env.prepend("PKG_CONFIG_PATH", pc_dst)   # 依赖 pc 所在目录
tc.generate()                             # ← 看似正确，实际丢失！
```

构建时 configure 报：

```
checking for LCMAPS_BASIC_INTERFACE... no
configure: error: no LCMAPS basic interface found
```

检查生成物 `conanautotoolstoolchain.sh`：只有 conan 默认的
`export PKG_CONFIG_PATH="$script_folder/..."`，**自定义 prepend 与 unset 均未出现**。

## 根因

conan 2.x `AutotoolsToolchain.generate(self, env=None, scope="build")` 的实现：

```python
def generate(self, env=None, scope="build"):
    env = env or self.environment()   # env=None 时新建！
    ...
```

而 `environment()` 每次调用都 `Environment()` 新建实例（CC/CFLAGS 等在其中
逐项 define）。所以 `tc.environment()` 返回的实例与 `generate()` 内部新建的
**不是同一个对象**——对其修改全部丢失，且无任何警告（静默）。

## 影响范围

- 所有 conanfile.py 里"取 tc.environment() 改一改再 generate()"的模式：
  PKG_CONFIG_PATH 注入、unset 污染变量、LD 相关覆盖……
- 同类 API 均需检查签名：`CMakeToolchain.generate()` 无 env 参数（无此坑），
  AutotoolsToolchain 有。

## 推荐方案

**方法**: `pass-modified-env-to-generate`

```python
tc = AutotoolsToolchain(self)
env = tc.environment()
env.prepend("PKG_CONFIG_PATH", pc_dst)
env.unset("C_INCLUDE_PATH")   # E075 防交叉污染
tc.generate(env=env)           # 显式传回同一实例
```

附带两个同族陷阱（同一次排障发现）：

1. **conanrunenv 只聚合直接 require 的 libdirs**：test_package 运行时
   `LD_LIBRARY_PATH` 不会自动含传递依赖包的 lib。test() 里手动构造：
   `self.run("LD_LIBRARY_PATH='<fw>/lib:<tested>/lib/lcmaps' '%s' '%s'" % ...)`。
2. **CMakeDeps 只为直接 requires 生成 config**：test_package 要 find_package
   传递依赖时，需显式 `self.requires("lcmaps/1.6.7")`（版本与主配方同步）。

## 验证命令

```bash
grep PKG_CONFIG_PATH <build>/generators/conanautotoolstoolchain.sh
# 修复后应含自定义路径；修复前只有 generators folder 默认值
```

## 取证记录

- 包: lcmaps-plugins-voms 1.7.1（`archives/l/lcmaps-plugins-voms/1.7.1`）
- 逐字证据: `reports/conan-create.log`（修复前后 configure 探测行
  `checking for LCMAPS_BASIC_INTERFACE... no/yes`）、test_package/conanfile.py
