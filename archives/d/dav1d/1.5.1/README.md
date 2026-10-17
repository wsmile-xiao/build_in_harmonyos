# dav1d 1.5.1 — 鸿蒙 PC conan 制品（1.5.0 升级件）

`os=OHOS, arch=armv8`(= aarch64) 的 conan 包，dav1d 1.5.0 的版本升级（1.5.1：looprestoration 重写降栈至 aarch64 58KB、flush() 死锁修复）。

## 出包（鸿蒙 PC CI）

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；推荐使用 OpenHarmonyPCDeveloper 分发的 conan（社区 PyPI 源）。

## 上游测试

本配方 `enable_tests=true`：`build()` 内 `meson.test()` 执行上游注册测试（6 个头文件 API 测试 + checkasm[asm 开启时]）。构建机为 OHOS aarch64 真机时原生执行；真交叉构建（非 OHOS 主机）时跳过执行只验编译（`cross_building` 守卫）。

## ELF 签名

**本 recipe 显式重签**：`package()` 调 `_sign_binaries()`，对 `lib/**/*.so*` 逐个 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`。

原因：cmake 走 SDK `ohos.toolchain` 产的 `.so` 自签无效（dlopen `Permission denied`）；而 install 阶段若复制或 strip 已链接产物，也会破坏链接器自签。**产可执行文件的包 `bin/` 必须一起签**——本包 `enable_tools=false` 无 bin 产物。

## 消费 A：conan 工程（CMake/pkg-config 消费本库）

```bash
conan install --requires=dav1d/1.5.1 -pr ohos-aarch64
```

生成 `dav1d-config.cmake` / `dav1d.pc`；`find_package(dav1d)` 消费，运行期 `source conanrun.sh`。

## 消费 B：裸程序（设备 ~/usr/local + dlopen）

```bash
conan install --requires=dav1d/1.5.1 -pr ohos-aarch64 \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

头文件/库/.pc 展开到 `~/usr/local/{include,lib,bin}`；裸 `dlopen` 全路径即可命中。

## 点对点搬运预编译包（免 remote）

```bash
conan cache save "dav1d/1.5.1:*" --file dav1d.tgz   # 出包机导出（recipe + 二进制）
conan cache restore dav1d.tgz                                # 目标机导入
```
