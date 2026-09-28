# DRAFT-windows-host-conan-create：Windows 宿主本机跑通 OHOS 交叉 conan create（build profile 必须 Windows；.cmd 编译器包装器）

> Draft（未 promote）— 来源于 fathom 1.0 适配（2026-09-27，conan 2.29.1 + DevEco SDK clang 15.0.4 实证全链路通过）
> 对应 `.kv` 文件同 stem：`DRAFT-windows-host-conan-create-cross-ohos-build-profile.kv`

## 症状

在没有真机/CI 窗口时想本机做 W3 级验证（`conan create` 全链路）。OHOS 适配版
conan 2.29.1 可从社区 PyPI 源装到 Windows（`pip install conan --index-url
https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple`），照抄
仓库 `ci/conan/profiles/ohos-aarch64` 把 **build profile 也写成 os=OHOS** 后，
`conan create` 在 `cmake.configure()` 处必死：

```
fathom/1.0: RUN: cmake -G "Ninja" -DCMAKE_TOOLCHAIN_FILE=...
'.' 不是内部或外部命令，也不是可运行的程序或批处理文件。
ConanException: Error 1 while executing
```

`'.'` 报错极具迷惑性——不是 cmake 找不到，也不是配方语法问题。

## 根因

build profile 描述的是**执行构建的机器**。它被写成 os=OHOS 后，conan 认为构建
环境是 POSIX：聚合环境文件只生成 `conanbuild.sh`（而非 `conanbuild.bat`），
`self.run()` 的命令前缀走 POSIX 的 `. source` 形式——在 Windows 宿主上由
cmd.exe 执行，cmd 把行首的 `.`（POSIX source 命令）当成程序名，于是报
"'.' 不是内部或外部命令"。

## 方案

双 profile 交叉：**build 用 Windows，host 用 OHOS**（CI/真机两者都是 OHOS，
所以仓库里只有单一 ohos profile；本机必须拆开）。

host profile（如 `~/.conan2/profiles/ohos-local`）：

```ini
[settings]
os=OHOS
os.version=6.0
arch=armv8
compiler=clang
compiler.version=15
compiler.libcxx=libc++
compiler.cppstd=17
build_type=Release

[conf]
tools.build:compiler_executables={"c": "C:/Users/<user>/ohos-cross/ohos-clang.cmd", "cpp": "...", "ar": ".../llvm-ar.exe", "ranlib": ".../llvm-ranlib.exe", "strip": ".../llvm-strip.exe"}
tools.cmake.cmaketoolchain:generator=Ninja
```

关键件：

1. **编译器包装器**（SDK 的 clang.exe 默认 target 是 x86_64-w64-windows-gnu，
   必须补 target+sysroot）。`ohos-clang.cmd`：
   ```bat
   @echo off
   "C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\native\llvm\bin\clang.exe" --target=aarch64-linux-ohos --sysroot="<SDK>\native\sysroot" %*
   ```
   CMake 的编译器探测能识别该包装器（"Check for working C compiler ... skipped"）。
2. **build profile**：`os=Windows, arch=x86_64, compiler=clang`（无需包装器，
   本 profile 不编译任何东西）。
3. cmake/ninja 用 SDK 自带的 `native/build-tools/cmake/bin`（独立安装的 CMake
   会缺 OHOS 平台模块——`System is unknown to cmake, create: Platform/HarmonyOS`
   警告无害，构建照常成功）。

运行：

```sh
conan create archives/<首字母>/<库>/<版本> -pr:h ohos-local -pr:b windows-build --build=missing
```

从 **PowerShell/cmd** 运行，不要从 Git Bash：MSYS 环境会让 conan 误生成
`.sh` 环境文件并走 sh 包装，同样的 `'.'` 报错会以另一种方式复现。

通过后包进本地缓存（settings os=OHOS arch=armv8），产物 ELF64/AArch64；
test_package 在 can_run=false 下走 compile+link 检查（交叉语义正确）。
配套验证：aarch64 消费者测试可在 linux 容器（gcc 同源码编译）实跑断言。

## 配套卫生（防止生成物污染后续传输）

本机 conan create 会在**包目录内**的 `test_package/` 下生成 `build/` 树和
`CMakeUserPresets.json`（cmake_layout 写入 recipe 同级）。之后若要把包目录
tar 传到真机 shadow CI，必须先删掉这两处再打包，并在设备端
`find <包目录> -type f | wc -l` 核对文件数（应恰好等于已提交的源文件数），
否则生成物会被当源文件带进设备端构建。

## 复用价值

无真机窗口/真机排队时，本机即可完成 W3 级"conan create + 产物架构验证 +
消费者测试编译链接"，把真机窗口留给最终执行验证。
