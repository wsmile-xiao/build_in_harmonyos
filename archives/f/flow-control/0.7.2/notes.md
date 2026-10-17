# flow-control 0.7.2 适配笔记

## 编译环境
- 构建系统: custom (zig build)
- 编译日期: 2026-08-20
- 编译器: clang/clang++ (OHOS SDK) + zig/0.15.2
- 状态: built (zig 依赖待发布，R36 阻塞属正常)
- 上游: https://github.com/neurocyte/flow v0.7.2 (f56313fd00a36ab04ee9a9ddb200aebf195df3882947a698c1d1760d4bbd1d4a)

## 编译步骤
```bash
# conan 配方 build() 实际执行：
ZIG_GLOBAL_CACHE_DIR=$BUILD_FOLDER/zig-global-cache \
ZIG_LOCAL_CACHE_DIR=$BUILD_FOLDER/zig-local-cache \
ZIG_OHOS_SIGN_ROOTS="$BUILD_FOLDER/zig-global-cache $BUILD_FOLDER/zig-local-cache $SOURCE_FOLDER/zig-out" \
zig build -Doptimize=ReleaseSafe --summary all
# 产物: $SOURCE_FOLDER/zig-out/bin/flow -> $PACKAGE_FOLDER/bin/flow (OHOS 上签名)
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Zig 在 OHOS 上探测宿主 libc 时引用 OHOS SDK clang 的 sysroot 头，`stdint.h` 依赖 `bits/alltypes.h` 无法解析，C 源码编译失败 | Zig 咨询 `CC`/`CXX` 环境指向的 OHOS SDK clang，注入 OHOS sysroot include dirs，其 musl 头不完整 | `build()` 中清理 `CC/CXX/CFLAGS/CPPFLAGS/LDFLAGS/CPATH/CPLUS_INCLUDE_PATH/C_INCLUDE_PATH`，让 Zig 回落自带 musl 头，21/21 steps 通过 |
| 2 | Zig 生成的宿主可执行文件（build runner、ts_bin_query_gen、uucode_build_tables）与最终 `flow` ELF 在 OHOS 上无法 spawn，报权限/签名错误 | OHOS 要求 ELF 带 codesign 段 | `zig/0.15.2` wrapper 自动签名中间 runner；最终 `zig-out/bin/flow` 在 `package()` 中通过 `binary-sign-tool`/`llvm-objcopy --remove-section .codesign` 自签名（`_is_ohos()` 时） |
| 3 | Zig 0.16.x 与 flow 不兼容 | 上游 `build.zig.zon` 声明 `minimum_zig_version = "0.15.2"` | `tool_requires("zig/0.15.2")` 精确锁定，`_zig()` 优先取 `dependencies.build["zig"].package_folder/bin/zig` |
| 4 | Zig cache 污染/签名根不一致 | 多次构建复用全局 cache，codesign 分区残留 | 隔离 `ZIG_GLOBAL_CACHE_DIR`/`ZIG_LOCAL_CACHE_DIR` 至 `build_folder`，`ZIG_OHOS_SIGN_ROOTS` 覆盖 global/local/zig-out 三处 |

## 源码修改
无补丁（`conandata.yml patches: {}`）。OHOS 适配完全在 `conanfile.py build()/package()` 中完成，未改上游源码。

## 依赖版本
- `zig/0.15.2` (tool_requires，PR#5562 待发布，本地缓存以 built 状态处理 R36 阻塞属正常)

## 验证结果
```bash
$ conan create archives/f/flow-control/0.7.2 --version 0.7.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 21/21 zig build steps succeeded
# package: bin/flow (ELF 64-bit LSB arm64, static, signed on OHOS)
$ flow --version  # -> unknown (未 embed version，仅 --help 可用)
$ flow --help     # -> Flow Control: a programmer's text editor
$ flow --list-languages  # -> 70+ languages
$ readelf -d bin/flow | grep NEEDED  # -> 无（静态）
```

## 交付物
| 文件 | 说明 |
|------|------|
| bin/flow | 静态 ELF 可执行文件，aarch64-linux-ohos |

## 注意事项
- 状态 `built`：依赖 `zig/0.15.2` 尚未发布到制品仓（R36 Hard Fail 属预期），`conan create --build=missing` 会从源码构建 zig；本地验证通过即视为 `built`
- OHOS 首次执行会弹安全确认框（R7）
- `/tmp` 只读，测试用 `$TMPDIR`
- `validate()` 仅接受 `Linux/OHOS`（R32），`build()` 不裸用 `${CC}` 等 shell 变量（R33）
- `test_package/test.sh` 真实执行 `flow` 二进制（R34），`commands.json` type=tool（R38）
---

**编译结束**: 2026-08-20 15:27
**最终状态**: built
