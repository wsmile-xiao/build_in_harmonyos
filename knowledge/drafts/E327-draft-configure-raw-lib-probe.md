# E327 知识草稿：自写 configure 用裸 -l 探测第三方库（不读 LDFLAGS）且 pkg-config 模块名不匹配

> 编号：E327（草稿，待 graph promote 转正式）
> 文件名：E327-draft-configure-raw-lib-probe
> 实例来源：coturn 4.7.0（archives/c/coturn/4.7.0）→ 依赖 openssl/3.5.6
> 检索字段：library=coturn / build=autotools / error=configure / toolchain=clang15 / platform=ohos / dependency=openssl

## 症状

conan create 在 configure 阶段中止：

```
Library option -lcrypto cannot be used
ERROR: OpenSSL Crypto development libraries are not installed properly in required location.
Abort.
```

（自写 configure 的 `testpkg_common libcrypto` 与 `testlib crypto` 两条探测路径都失败。）

## 根因

coturn 的 configure 是**自写脚本**（非 autoconf 生成），探测第三方库时用
`${CC} ${TMPCPROGC} ... ${OSCFLAGS} ${OSLIBS} -lcrypto` 这类**裸命令**：
只拼接脚本内部累积的 OSCFLAGS/OSLIBS，**不读** conan 注入的 LDFLAGS/CPPFLAGS
环境变量，所以 conan 缓存里 openssl 的 `-L` 路径根本到不了探测链接。

同时它用 pkg-config 按上游模块名查询 `libcrypto`/`libssl`，而 conan 的
`PkgConfigDeps` 只按配方 `pkg_config_name`（未设置时取包名）生成 `openssl.pc`，
不存在 `libcrypto.pc` → pkg-config 路径也失败。两条路都走不通，configure 中止。

## 解决方案

使用 configure 脚本**自身文档化的覆盖变量**。coturn configure 第 756 行：
同时设置 `SSL_CFLAGS` 与 `SSL_LIBS` 时走 "Private SSL Library option" 分支，
直接用这两个变量编译/链接探测程序，并把它们写进生成的 Makefile（OSCFLAGS/OSLIBS）。

conanfile.py build() 中：

```python
openssl = self.dependencies["openssl"].package_folder
build_env.define("SSL_CFLAGS", f"-I{os.path.join(openssl, 'include')}")
build_env.define("SSL_LIBS", f"-L{os.path.join(openssl, 'lib')} -lcrypto -lssl")
```

先例：libp11 用 `OPENSSL_CFLAGS`/`OPENSSL_LIBS` 解决同一类问题。

## 影响范围与推广价值

- 所有用自写 configure 探测第三方库、且依赖配方未声明与上游一致的多
  pkg_config_name 的软件（coturn、libp11 同类）。
- 方案不修改依赖配方、不改缓存、不 sed 源码，只动消费方 conanfile 的
  Environment，可复用性强。

## 验证

- 本地以 conan 缓存 openssl 路径 + 相同 env 跑 configure → 全部探测通过、
  Makefile 生成成功；`make -j1` 构建出全部 bin/ 产物；
  `./bin/turnserver --version` 输出 `4.7.0`。
- 关联 PR：#5581（feat/coturn-4.7.0）。
