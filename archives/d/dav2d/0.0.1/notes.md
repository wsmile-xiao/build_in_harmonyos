# dav2d 0.0.1 适配笔记

## 编译环境

- 构建系统: meson（纯 C 配置）
- 上游: VideoLAN dav2d（AV2 解码器，dav1d 的后继项目），tag `0.0.1`
- 编译日期: 2026-09-10
- 编译器: clang/clang++（OHOS aarch64 真机工具链）
- 状态: built（配方已完成，待 HMBS 真机预检）

## 上游源码核实

- 规范仓库为 https://code.videolan.org/videolan/dav2d（GitHub 上无 videolan 官方镜像，只有个人 fork，不可用）。
- `conandata.yml` 使用官方 GitLab 归档地址：
  `https://code.videolan.org/videolan/dav2d/-/archive/0.0.1/dav2d-0.0.1.tar.gz`
- sha256 以真机实测下载值为准（官方 GitLab 归档 URL 保持不变）：
  `1b0874984cb29b96f59c8b24f109a5707e4917d2e7d45d57d482ae0473d8c627`。
  2026-09-09 真机预检 `get()` 实测下载同一官方归档计算值为 `1b0874...`，与原记录值 `e3eec3...`不一致；原 MacPorts 交叉参考无法验证（未找到 dav2d 的 MacPorts Portfile），故以真机实测值为准更正，URL 保持不变。

## 编译步骤

Conan 配方（`conan create`）全自动完成，Meson 配置如下：

```bash
-Ddefault_library=shared
-Denable_asm=false
-Denable_tools=false
-Denable_examples=false
-Denable_tests=true
-Denable_docs=false
-Dtestdata_tests=false
-Dwrap_mode=nodownload
```

只安装库头文件（`include/dav2d/*.h`）与 `libdav2d.so*`，不产出 CLI 工具
（`enable_tools=false`，故无需 `commands.json`）。

## 上游测试审计（源码级）

`tests/meson.build`（0.0.1 附近主干一致）在本配置下注册的测试：

| 测试 | 来源 | 本配置是否执行 |
|------|------|---------------|
| `common.h_test` 等 6 个 header 测试 | `tests/header_test.c` × `include/dav2d/meson.build` 的 6 个 API 头 | 执行（`meson test`） |
| `checkasm` | 需 `enable_asm=true` + 外部 checkasm wrap | 不执行（纯 C 配置） |
| testdata 套件 | 需另行克隆 `tests/dav2d-test-data` 且 `-Dtestdata_tests=true` | 不执行 |
| libfuzzer 二进制 | 随测试构建产物编译，非注册 `test()`，需语料才有意义 | 构建但不执行 |

配方 `build()` 末尾用 `meson test -C <build> --print-errorlogs` 真实执行并
解析汇总行，输出 `HMBS_UPSTREAM_TEST_RESULT` 标记；失败/跳过/零执行一律抛
异常，不伪造通过。 verdict 同步持久化进包内 `res/upstream_test_result.json`，
`test_package` 每轮复发（包缓存命中时 `build()` 不重跑）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 上 Meson machine file 里的编译器是 shell 脚本包装，Meson 无法直接执行 | 与 libdav1d 1.5.4 相同的 runner 环境 | 按 libdav1d 方案把 machine file 改写为 `[shell, compiler]` 数组 |
| 2 | `clock_gettime` 探测在 musl + 纯 C99 下失败会导致 configure 直接 `error` | meson.build 只对 linux/gnu/emscripten 加 `-D_GNU_SOURCE`，OHOS 命中不到 | OHOS `c_args` 注入 `-D_POSIX_C_SOURCE=200809L`（libdav1d 实证） |
| 3 | Meson compile-only 探针遇 OHOS clang 包装器的链接器参数报 `-Werror=unused-command-line-argument` | 同 libdav1d finding #3 | OHOS `c_args` 追加 `-Qunused-arguments` |
| 4 | Meson 按裸名 `llvm-ar` 找归档器，PATH 上没有 | Conan MesonToolchain 不写 ar/ranlib 进 native file | 从 C 编译器同目录推导绝对路径注入 machine file |
| 5 | 真机无全局 `meson` 可执行文件 | 预检设备只注入 cmake/make/ninja/python3 | `_ensure_meson()`：优先复用设备 python3 的 `mesonbuild` 模块，否则下载 meson 1.5.1 源码包自举（criterion 同款，镜像优先、官方兜底、sha256 校验） |
| 6 | Meson install 在该 worker 上可能跳过版本化 `.so` 软链 | 与 libdav1d 相同的 worker 限制 | `package()` 把 `libdav2d.so[.1[.0.0]]` 别名复制为实体文件 |
| 7 | HarmonyOS PC XPM 要求 dlopen 的 `.so` 代码签名 | 工具链自签在 conan install 复制后失效 | `binary-sign-tool -selfSign 1` 重签 `lib/` 下全部 ELF |

## 依赖版本

- 无 Conan 依赖（`requirements()` 为空，`wrap_mode=nodownload` 禁止 Meson 自行拉取子项目）。
- 系统库：`pthread`、`libm`（OHOS musl 由 libc 提供）。
- 构建期自举（仅真机缺 meson 时）：meson 1.5.1 源码包。

## 验证结果

本地静态检查（本机可执行部分）：

```bash
python -m py_compile archives/d/dav2d/0.0.1/conanfile.py archives/d/dav2d/0.0.1/test_package/conanfile.py
git diff --check -- archives/d/dav2d
```

真机验证（HMBS 预检，`conan create` + `meson test` 6 项 + `test_package`
7 断言）待本轮结束后由后台执行，结果回填 manifest 与 PR 正文。

## 注意事项

- `code.videolan.org` 在本机网络后有 Anubis 人机验证，直接下载会拿到挑战页；
  真机/CI 网络已有 libdav1d 1.5.4 同源下载成功的先例，不影响预检。
- 本版为 dav2d 首个上游版本（AV2 规范未冻结，上游自述不宜生产使用）；
  配方只做基础适配（路径 A），不做 API 扩展。
