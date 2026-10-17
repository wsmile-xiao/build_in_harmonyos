# DRAFT: AC_CHECK_LIB 缺依赖时只警告——二进制照样产出，运行期静默空输出或 SIGSEGV

> Contributor: username- | Status: DRAFT | Created: 2026-09-17
> 来源: libdv-tools 1.0.0 适配（encodedv / dubdv / dvconnect 用 popt 解析命令行）

## 症状

`conan create` 的构建阶段一路绿灯，打包完成，`test_package` 才炸：

```
[test] encodedv --version
encodedv --version did not report a version:      <- 输出是空的，退出码 0
```

本地用同一份源码复现，裸跑更直接：

```
$ ./encodedv
Segmentation fault        # 退出码 139
```

而 `configure` 的日志里只有一行轻描淡写的：

```
checking for poptGetContext in -lpopt... no
```

## 根因

autotools 里可选依赖的惯例写法是：

```m4
AC_CHECK_LIB([popt], [poptGetContext])
```

找不到库时它**不失败**，只把结果写成 `config.h` 里的注释：

```c
/* #undef HAVE_LIBPOPT */
```

源码里整块 `#if HAVE_LIBPOPT` 就被预处理器消掉了。libdv 1.0.0 被消掉的正好是
选项表、`--version`、`--help` 和 usage，只剩下：

```c
filename = argv[1];      /* 裸跑时 argv[1] == NULL */
```

于是 `--version` 既不打印也不报错（退出 0），裸跑直接段错误。
**"构建成功"和"程序可用"在这里完全脱钩**，只有真机执行才暴露。

交叉构建会放大这个问题：`AC_CHECK_LIB` 只用 `$LIBS` / `$LDFLAGS` 里的搜索路径，
conan 的 `AutotoolsToolchain` 不保证把依赖包的 `-L`/`-I` 放进那条链接检查，
所以"已经 `requires()` 了"≠"configure 找得到它"。

## 修复

**1) 把可选依赖提成硬依赖**，保证它一定在场：

```python
def requirements(self):
    self.requires("popt/1.16")
```

**2) 显式把它的搜索路径喂给 configure：**

```python
popt = self.dependencies["popt"]
tc.extra_cflags.append(f"-I{os.path.join(popt.package_folder, 'include')}")
tc.extra_ldflags.append(f"-L{os.path.join(popt.package_folder, 'lib')}")
```

**3) 在 `configure()` 之后立刻断言 `config.h`**，把"静默降级"变成构建期失败：

```python
for base in (self.build_folder, self.source_folder):
    config_h = os.path.join(base, "config.h")
    if os.path.isfile(config_h):
        with open(config_h, encoding="utf-8", errors="replace") as fh:
            if "#define HAVE_LIBPOPT" not in fh.read():
                raise ConanException("configure did not detect popt ...")
        break
```

## 两个容易写错的断言

**断言不能写成 `"HAVE_LIBPOPT" in text`。** autoheader 把否定结果写成
`/* #undef HAVE_LIBPOPT */`，这个字符串里同样含 `HAVE_LIBPOPT`，
于是断言恒真——配方"看起来做了检查"，实际永远不报错。必须写成
`"#define HAVE_LIBPOPT"`。

**退出码不能简单用 `rc >= 128` 判崩溃。** 这些工具对"没给文件名"的回应是
`exit(-1)`，shell 把它报成 255，也在 128 以上。要区分信号死亡，只能枚举
真正的信号状态（139=SIGSEGV、134=SIGABRT……），或者干脆断言"输出非空"。

## 验证

```sh
grep -n '#define HAVE_LIBPOPT' config.h    # 必须命中
grep -n 'HAVE_LIBPOPT' config.h            # 注释形式也会命中，不能当判据

<pkg>/bin/encodedv --version               # 退出 0 且输出非空
<pkg>/bin/encodedv                         # 普通非零退出，不能是 139
```
