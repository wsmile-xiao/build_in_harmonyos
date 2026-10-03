# autotools 交叉适配 OHOS：config.sub 不认 `aarch64-linux-ohos`，`--CPPFLAGS` 被拒，依赖路径不会自动注入

> Draft: `DRAFT-AUTOTOOLS-OHOS-TRIPLET-AND-PRECIOUS-VARS`
> Stem: `autotools-ohos-triplet-and-precious-vars` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-AUTOTOOLS-OHOS-TRIPLET-AND-PRECIOUS-VARS
- **严重度**: 1
- **类别**: build|portability|ohos-platform|autotools
- **触发工具**: conan|autoreconf|configure|make
- **阶段**: configuration

## 三个连续坑

适配 rt-app 时按顺序踩到的三个错误，每个都会让人误判方向：

```
# 1) triplet 不被接受
configure: error: unrecognized option: `--host=aarch64-linux-ohos'
#   实际信息：Invalid configuration `aarch64-linux-ohos': OS `ohos' not recognized

# 2) 依赖路径靠命令行传不进去
configure: error: unrecognized option: `--CPPFLAGS=-I/.../json-.../p/include'
configure: error: unrecognized option: `--cppflags=-I/.../json-.../p/include'   # 大小写都不行

# 3) 路径压根没注入，编译期才发现
src/rt-app_parse_config.c:28:10: fatal error: 'json-c/json.h' file not found
```

外加一个布局坑：

```
autoreconf: error: 'configure.ac' is required
```

## 根因

**一、config.sub 不认 OHOS。** Conan 对 `os=OHOS` 推导出的 triplet 是 `aarch64-linux-ohos`，
而 automake 1.16 自带的 `config.sub` 只接受已知 OS 名称：

```bash
config.sub aarch64-linux-ohos          # -> Invalid configuration: OS `ohos' not recognized
config.sub aarch64-linux-gnu           # -> aarch64-unknown-linux-gnu   ✅
```

**二、precious variable 必须先声明。** `--CPPFLAGS=` / `--LDFLAGS=` 只有在 `configure.ac`
里用 `AC_ARG_VAR([CPPFLAGS], ...)` 声明之后才被 configure 识别；未声明时两种大小写拼写
一律 `unrecognized option`。

**三、`AutotoolsToolchain` 不注入依赖路径。** 它只生成
`CC / CFLAGS / CXXFLAGS / LDFLAGS(defines) / PKG_CONFIG_PATH`，
**不遍历 `self.dependencies` 去加 `-I` / `-L`**。rt-app 用
`AC_CHECK_LIB([json-c], [json_object_from_file])` 而不是 `PKG_CHECK_MODULES`，
所以 pkg-config 生成器帮不上忙，`--cppflags` 传了也等于没传。

**四、`basic_layout` 的 cwd。** `self.run()` 默认 cwd 是 `build-release` 子目录，
里面没有 `configure.ac`，手写 `self.run("autoreconf ...")` 必然报缺文件。

## 影响范围

- 所有满足"configure.ac 未声明 `AC_ARG_VAR` + 用 `AC_CHECK_LIB` 找依赖"的 autotools 包，
  在 OHOS 或任何交叉场景下都会踩。
- 只跑到 `conan create` 的包，会在依赖头文件这一层才暴露问题，返工成本高。

## 推荐方案

**方法**: `pin-triplet-to-aarch64-gnu-and-pass-dep-flags-via-env`

### 1) 把 triplet 钉成 canonical aarch64

```python
tc = AutotoolsToolchain(self)
tc.configure_args += ["--host=aarch64-linux-gnu", "--build=aarch64-linux-gnu"]
tc.generate()
```

`aarch64-linux-gnu` 会被 `config.sub` canonical 成 `aarch64-unknown-linux-gnu` 并接受，
而编译器驱动仍按 `--target=aarch64-linux-ohos` 产出对象、链接 OHOS sysroot。
**同时钉 `--build`** 可让"原生 OHOS runner"与"交叉宿主"两种环境行为一致。

> 适用前提：包内**没有 `AC_RUN_IFELSE`**（rt-app 没有）。若包里有能运行编译产物的检查，
> 声明成 native 形态会让 configure 尝试执行 aarch64 程序；那种情况应改为给 `config.sub`
> 补 `linux-ohos` 分支（dnsperf 的 0001 补丁即是此法）。

### 2) 依赖路径走环境变量前缀，不走 `--CPPFLAGS`

```python
def _dependency_flags(self):
    inc_flags, lib_flags = [], []
    for dep in self.dependencies.values():
        for d in dep.cpp_info.includedirs:
            inc_flags.append("-I" + os.path.join(dep.package_folder, d))
        for d in dep.cpp_info.libdirs:
            lib_flags.append("-L" + os.path.join(dep.package_folder, d))
    return inc_flags, lib_flags
```

每个 `-I` / `-L` 都落在**依赖包自己的 conan 包目录**里（本构建私有的 prefix），
绝不写共享 `/usr/local`（R49）。拼进 configure 命令的环境前缀：

```python
self.run('CPPFLAGS="%s" LDFLAGS="%s" "%s/configure" %s'
         % (cppflags, ldflags, self.source_folder, " ".join(configure_args)))
```

### 3) autoreconf 用 Autotools 助手

```python
autotools = Autotools(self)
autotools.autoreconf(args=["--install", "--force"])   # 默认在 source_folder 执行
```

若坚持手写 `self.run("autoreconf ...")`，**必须**显式 `cwd=self.source_folder`。

## 验证命令

```bash
config.sub aarch64-linux-ohos                 # 复现坑 1
config.sub aarch64-linux-gnu                  # 期望 aarch64-unknown-linux-gnu
grep -rn "AC_ARG_VAR" configure.ac            # 期望无 CPPFLAGS/LDFLAGS ⇒ 复现坑 2
grep -rn "AC_CHECK_LIB\|PKG_CHECK_MODULES" configure.ac   # 复现坑 3

conan create . --name=rt-app --version=1.0 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
```

## 取证记录

- 包: rt-app 1.0（`archives/r/rt-app/1.0`）
- 环境: OHOS aarch64，clang 15.0.4，profile `ohos-aarch64-wsl`
- 同仓可对照的先例：`archives/a/a52dec/0.7.4`（同样钉 aarch64 主机三元组 + config.sub 补丁）、
  `archives/d/dnsperf/2.15.1`（同样从 `cpp_info.includedirs/libdirs` 注入依赖路径）