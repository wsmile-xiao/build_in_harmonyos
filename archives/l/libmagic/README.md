# libmagic

file(1) 命令与 libmagic 库：从文件签名识别文件类型。

- 上游主页: https://www.astron.com/pub/file/
- 上游源码: https://astron.com/pub/file/file-5.48.tar.gz
- License: BSD-2-Clause

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 5.48 | built | HarmonyOS PC (OHOS AArch64) 适配，零 patch |

## 说明

- 构建系统 autotools；`conan create` 期间在 build() 内执行上游正式测试
  （`make check` 的 check-local 套件，83 用例全过）并打印
  `HMBS_UPSTREAM_TEST_RESULT` 证据行。
- 零 patch：HMFS 的 configure umask/getcwd 问题沿用仓库判例（build() 内
  sed 修复），交叉三元组用 `aarch64-unknown-linux-musl` 规避 config.sub
  不识别 `ohos`。
- 构建期 magic.mgc 编译：交叉模式下传带路径的
  `FILE_COMPILE=$PWD/src/file`（构建宿主即 HarmonyOS AArch64，target
  file(1) 可直接运行；路径含 `/` 时上游跳过系统版本检查）。详见
  `notes.md`。
- 零依赖：上游测试集不需要解压库（flags 无 `-z`），CI L0i 亦要求依赖必须
  已发布。`--disable-zlib` 等全部关闭。

## 使用

```conan
requires = "libmagic/5.48"
```

CMake `find_package(libmagic)` 后链接 `libmagic::libmagic`，或 pkg-config
`libmagic`。头文件 `magic.h`，库 `libmagic.a`，`file(1)` 装在 `bin/`，
数据库 `share/misc/magic.mgc`。
