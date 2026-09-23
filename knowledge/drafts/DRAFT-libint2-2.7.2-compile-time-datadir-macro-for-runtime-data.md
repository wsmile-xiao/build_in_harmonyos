# 运行期数据目录靠编译期宏定位（DATADIR / LIBINT_DATA_PATH）

**草稿条目**（`DRAFT-libint2-2.7.2-compile-time-datadir-macro-for-runtime-data`）
来源：libint2 2.7.2 Conan 适配（2026-09-13）。

## 现象

按名加载基组（`libint2::BasisSet("sto-3g", atoms)`）依赖包内数据目录
`share/libint/2.7.2/basis/*.g94`。若消费者侧没有把数据目录"告诉"头文件，
`data_path()` 会退回构建期写死的绝对路径，在消费者机器上不存在；
而 `throw_if_no_match` **默认 false**，于是表现为：

```console
$ ./consumer          # BasisSet("sto-3g", water)
[INFO] nbf = 0        # 静默空基组，无任何报错
```

## 根因

上游 `basis.h.in::data_path()` 的判定顺序（编译期 + 运行期混合）：

```
1. 环境变量 LIBINT_DATA_PATH
2. 编译期宏 DATADIR
3. 编译期宏 SRCDATADIR
4. configure 期写死的 @DATADIR_ABSOLUTE@（= 构建时 CMAKE_INSTALL_PREFIX）
```

数据本身由 `install(DIRECTORY lib/basis DESTINATION share/libint/<ver>)` 安装，
Conan 打包后落在 `<package_folder>/share/libint/<ver>/basis`。
上游 CMake config 会通过 `INTERFACE_COMPILE_DEFINITIONS` 传 `DATADIR`，
但 Conan 消费者拿到的是 `cpp_info`，**不会**自动带上这个宏。

## 推荐方案

```python
def package_info(self):
    self.cpp_info.defines.append(
        f'DATADIR="{os.path.join(self.package_folder, "share", "libint", "2.7.2")}"'
    )
```

- 用 `self.package_folder` 拼接：`package_folder` 在**消费侧**解析，因此不会把构建机路径写死；
- 注意上游语义（libint2 会在 `DATADIR/basis` 与 `DATADIR` 两处探测，见 `basis.h` 注释）；

## 验证方式（要有正负两面）

```cpp
// 正向：按名加载得到预期基函数数
BasisSet("sto-3g", water).nbf() == 7
// 负向 1：默认语义下未知名 → 空基组（如实记录上游 API 语义）
BasisSet("no-such-basis", water).nbf() == 0
// 负向 2：strict 模式必须抛异常，且异常信息里出现真实数据目录 → 证明 DATADIR 生效
BasisSet("no-such-basis", water, /*throw_if_no_match=*/true)  →  异常含 "<pkg>/share/libint/2.7.2/basis/"
```

负向 2 是关键：只做正向断言的话，"数据目录其实指向源码树"这种错误配置也能通过。

## 回退方案

消费者设置 `LIBINT_DATA_PATH` 环境变量。可用但脆弱（依赖每个消费者的运行环境），
并且 `conanrun` 环境不一致时会再次静默降级。

## 禁忌

- **不要**让测试去读构建期源码树里的数据目录 —— 那会绕过"包内数据是否装全"这件事，
  漏装 `share/` 的缺陷会直接流到真实用户手里。
- **不要**在 define 里手写绝对路径；必须用 `self.package_folder` 拼接。

## 可复用判据

凡上游把运行期数据装在 `share/` 下、且定位方式包含**编译期宏**或 configure 期绝对路径，
就检查两件事：① `package_info()` 是否补了对应 define；② 该 API 的"找不到数据"路径是否会
抛异常（静默降级类 API 必须补负向断言）。
