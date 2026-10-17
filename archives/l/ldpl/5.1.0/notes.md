# ldpl 5.1.0 — HarmonyOS PC (OHOS aarch64) 适配笔记

任务：#8059（主活动「开源鸿蒙PC专项积分赛」）· 分支 `feat/ldpl-5.1.0` · 领取 2026-10-02T19:16:58Z

## 1. 上游与版本坐标

- LDPL = Logic Design Programming Language，一种 COBOL 风格语言，实现是一个 **转译器**：
  `src/ldpl.cpp` 单文件 C++（含 `aux/*.cpp`），把 `.ldpl` 源码翻译成 C++ 后调用系统 C++ 前端编译。
- 任务版本 `5.1.0` == 上游 tag `LDPL-5.1.0`（代号 "Groovy Gualicho"）。
  交叉验证：Homebrew formula `ldpl` 的 `versions.stable` = 5.1.0，`urls.stable.checksum`
  与 `conandata.yml` 的 sha256 `f61c0a8a…2701` 一致；归档顶层目录 `ldpl-LDPL-5.1.0/`。
- 外部依赖 **0 个**（`BigInt.hpp` 是树内 vendored）。归档 2.4 MB / 84 个条目，CI git-clone 无压力。

## 2. 构建

上游 `makefile` 的 `all` 目标只有一行：

```
cd src && $(CXX) -Wall -std=gnu++11 -fpermissive -DVERSION=… -DLDPLLIBLOCATION=… ldpl.cpp -o ldpl
```

两点不能直接用：

1. 非 Darwin/Android 分支会附加 `LFLAGS = -static-libgcc -static-libstdc++`。
   OHOS SDK（harmonybrew `ohos-sdk@26.0.0.18`）只提供 libc++，没有可静态链的 libstdc++ 归档。
2. `all` 里的 `cd src` 之后又 `mv src/ldpl build`，与 conan 的 out-of-source 布局打架。

所以 `build()` 直接执行该命令的等价形式（保留 `-std=gnu++11 -Wall -fpermissive` 与全部
`-D` 宏，去掉 `-static-lib*`），产物路径用绝对 `-o`。编译器取自
`tools.build:compiler_executables`（R33：不靠裸 PATH）。

## 3. 本版本真正的坑：转译器的两个运行期外部依赖

`ldpl` 装好之后，**跑起来**还需要两样东西，而这两样在上游代码里都是写死的：

| 运行期需要 | 上游写法 | OHOS 上的事实 |
|---|---|---|
| `ldpl_lib.cpp` + `BigInt.hpp` 的位置 | 编译期宏 `LDPLLIBLOCATION`（= `$(PREFIX)/lib/ldpl`） | 若按 conan 习惯填 `self.package_folder`，这个绝对路径会被烧进二进制；制品仓下载方在消费机上指向的是**构建机**的路径，必然不存在 |
| 一个 C++ 前端 | 字面量 `"c++ ldpl-temp.cpp …"`（5.1.0 没有 `-c=` 选项，也没有 `getenv`） | 真机 `command -v c++ / g++ / cc` **全部 MISSING**，PATH 上只有 `clang++`。上游文档 index.md 自己写明「必须把某个 C++ 编译器映射成 PATH 上的 `c++`」——这就是本平台的硬缺口 |

处置：`patches/0001-runtime-lib-location-and-cxx-override.patch`（53 行，portability，
**不含任何平台条件编译宏**）把这两处从「编译期常量」降级为「默认值」——优先读环境变量
`LDPL_LIB_LOCATION` / `LDPL_CXX`；`package_info()` 再用 `runenv_info.define_path`
把 `LDPL_LIB_LOCATION` 指到本机实际安装目录。于是包可重定位，消费者只要给出
`LDPL_CXX` 就能用，不需要在 PATH 上伪造一个叫 `c++` 的东西去污染全局。

## 4. 上游测试清点（为什么是 0/0）

```sh
tar tzf ldpl-5.1.0.tar.gz | wc -l                       # 84
tar tzf ldpl-5.1.0.tar.gz | grep -cE '/(tests?|test)/'  # 0
```

`LDPL-5.1.0` 归档里没有测试目录，`makefile` 的目标只有
`all / man / clean / install / uninstall`，`src/CMakeLists.txt` 里只有一个
`add_executable(ldpl)`。LDPL 仓库现在的 `tests/{expressions,features,structures}`
是 5.1.0 **之后**引入的，不在本版本坐标内；按规则禁止用 master/main 顶替版本号，
所以这里不拿它充当 5.1.0 的用例。上游用例数记 **0/0**，质量证据全部落在
`test_package/test_ldpl.sh` 的 26 项端到端断言（见 `test_package/MANIFEST.yml`）。

## 5. 语法样例的取数依据（避免"猜语法"白跑真机）

- tokenizer 对**非字符串** token 一律 `toupper`（`aux/aux_tokenizer.cpp:57`），
  所以 `data:` / `DATA:`、`display` / `DISPLAY` 等价；docs 的小写样例是有效的。
- `CRLF` 与 `LF` 都被替换成 `"\n"`（`ldpl.cpp:133`），**不产生 `\r`** → 输出可以按 LF 精确比对。
- 兜底语法错误：任何匹配不上的语句走 `badcode("Malformed statement")` → `error()` → `exit(1)`，
  报错前缀 `LDPL Error:`（`aux/aux_info.cpp:101`）。
- 生成的可执行文件名：取源码名到第一个 `.` 为止再加 `-bin`（`hello.ldpl` → `hello-bin`）。

## 6. 待真机确认的点

- `ldpl_lib.cpp` 用了 `<thread>`，链接是否需要 `-f=-pthread`（消费者测试已默认加上）。
- toybox 的 `od -An -c` 是否可用（ELF magic 断言）；不可用则改判据，不影响其余 25 项。
- clang 15 对 `-std=gnu++11 -fpermissive` 的接受度（上游只用过 g++）。
