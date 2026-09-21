# DRAFT-libfs-xorg-malloc0-cross-probe

## 现象

HarmonyOS PC 上为 libFS 1.0.10 跑 Conan 交叉构建（host profile
`ohos-aarch64`，configure 带 `--host=aarch64-linux-ohos --build=x86_64-linux-gnu`），
configure 在探测 malloc 语义时中止：

```
checking whether malloc(0) returns NULL... configure: error: in '.../build-release':
configure: error: cannot run test program while cross compiling
See 'config.log' for more details.
```

## 根因

X.Org `util-macros` 的 `XORG_CHECK_MALLOC_ZERO` 宏把选项
`--enable-malloc0returnsnull` 的默认值设为 **auto**。auto 分支的逻辑
（libFS 1.0.10 生成的 configure 第 20156 行起）：

1. `MALLOC_ZERO_RETURNS_NULL=auto` 时进入 `xorg_cv_malloc0_returns_null` 探测；
2. 若缓存未设置且 `cross_compiling=yes`，`ac_fn_c_try_run` 无法在构建机运行
   host conftest → `as_fn_error "cannot run test program while cross compiling"`，
   configure **直接中止**（不是默认值兜底）。

即：该宏在交叉编译下没有安全默认路径，只要进入 auto 分支必炸。这是所有使用
`XORG_CHECK_MALLOC_ZERO` 的 X.Org 库的共性问题（libXres 1.2.1 适配时已遇到
同款并修复），非 libFS 特有。

与 `AC_FUNC_MALLOC`/`rpl_malloc`（draft：DRAFT-ohos-autotools-rpl-malloc）
区分：那是 autoconf 内置宏交叉下误判 `ac_cv_func_malloc_0_nonnull=no` 后
**宏替换** `malloc`→`rpl_malloc`，链接期才报 undefined symbol；本条是
X.Org 宏的运行期探针在 **configure 阶段**直接中止，错误签名完全不同。

## 修复

configure 追加一个参数即可：

```
--disable-malloc0returnsnull
```

选项解析（configure 第 20146 行）：`enable_malloc0returnsnull` 被显式设置时
`MALLOC_ZERO_RETURNS_NULL=$enableval`，不再为 auto，跳过运行探针；
`--disable` 置 no → `MALLOC_ZERO_CFLAGS` 为空（库不假设 malloc(0) 返回
NULL，不加防御代码）。OHOS musl 的 `malloc(0)` 返回可用的非 NULL 指针，
置 no 与目标平台实际语义一致（同 glibc 语义）。

### 实现细节踩坑（Conan 配方）

libfs 配方 OHOS 路径手工拼 configure CLI，从 `AutotoolsToolchain` 实例取
`configure_args`。首次修复时把 `--disable-malloc0returnsnull` append 到
`generate()` 里构造的实例上，而 `_configure_ohos` 又 new 了另一个实例取
`configure_args` —— 参数静默丢失，构建再次以相同错误失败（两次失败签名
相同，容易误判为“参数无效”）。修正：append 到实际被取值的那个实例。

教训：手工拼 CLI 的配方里，所有 configure 参数必须在**取值处**的同一实例上
追加，或统一从文件/env 读取；跨实例 append 不生效且无任何警告。

## 验证

- 修复前：`conan create ... -pr:h ohos-aarch64 -pr:b ohos-aarch64 -o shared=True`
  在 configure 阶段报上述错误（config.log 命令行确认无该参数）。
- 修复后：configure 通过，`make -j1`、`make -j1 check`、`make install`、
  test_package（API 契约 + ELF64 AArch64 检查）全绿；shared 与 static
  双模式均验证通过。
- 同款先例：`archives/l/libXres/1.2.1/conanfile.py` 第 133-138 行注释与
  `--disable-malloc0returnsnull`，交叉印证该根因与修复的可复用性。

## 适用面

任何在交叉编译环境（不只 OHOS）构建且 `configure.ac` 含
`XORG_CHECK_MALLOC_ZERO` 的 X.Org 库。查 `configure --help` 输出中出现
`--enable-malloc0returnsnull` 即可预判。
