# sideretro 1.1.6 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-21
- 编译器: clang/clang++ (OHOS SDK 26)
- 状态: built

## 编译步骤

```bash
# 依赖注入（zlib/sqlite3/htslib/check 均从 conan 制品仓发布）
conan create archives/s/sideretro/1.1.6 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

构建采用 PkgConfigDeps + MesonToolchain。`generate()` 注入依赖 .pc 与工具链
ar/ranlib/pkg-config；引入 SDK libc++ 目录到 LD_LIBRARY_PATH 以满足 OHOS 下
ninja（C++ 动态链接二进制）运行；上游 185 项 check 单元测试随 `meson.test()`
纳入 conan create 全量执行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson setup: Could not detect Ninja v1.8.2 or newer | OHOS ninja 为 C++ 动态链接 ELF，运行时缺 libc++_shared.so（报 EPERM，meson 误判为未安装） | conanfile `_build_environment()` 注入 SDK `.../llvm/lib/aarch64-linux-ohos/c++` 到 LD_LIBRARY_PATH |
| 2 | src/utils.c:241 char* = int 编译错误 | 上游用 glibc 专有的 `secure_getenv()`，OHOS libc（非 glibc）不声明该函数，隐式声明返回 int | 补丁 0001：`while`/测试改用 `getenv()`（sideRETRO 非 setuid，语义等价；避免 __OHOS__ 平台宏） |
| 3 | 上游 185 项测试 49 项 "Early exit with return value 1" | 测试硬编码 `/tmp/ponga*` 临时文件路径，OHOS `/tmp` 只读（errno=30） | 补丁 0002-0020：`/tmp/` 前缀相对化为 `./ponga*`（meson test CWD=构建目录可写） |
| 4 | check_sider_gz test_read_fatal1/2 超时 | 上游测试在 `gzclose()` 后继续 `gz_getline`（use-after-free），OHOS zlib 缓冲残留导致死循环 | 补丁 0013：改为读取"合法 gzip 头+截断 deflate"的损坏文件，确定性触发 `gz_check_error→log_fatal` |
| 5 | test_package 运行 sider EPERM (Operation not permitted) | `meson install` 剥离二进制 RUNPATH，改写动态段导致 OHOS `.codesign` 签名失效，沙箱拒绝 exec | package() 不再用 `Meson.install()`，直接复制 build 产物 sider（保留签名）；运行时依赖由 conanrun 环境 LD_LIBRARY_PATH 提供 |

## 源码修改

- 补丁 0001：`src/utils.c` `secure_getenv` → `getenv`（which 路径查找）
- 补丁 0002-0020：18 个测试文件 `/tmp/` 前缀相对化为 `./`
- 补丁 0015：`tests/check_sider_main.c` `secure_getenv` → `getenv`（LOG_DEBUG_KEY）
- 补丁 0013：`tests/check_sider_gz.c` 新增 create_corrupt_gz，重写 test_read_fatal1/2 确定性触发
- 全部补丁为 portability 修复，不含 `__OHOS__` 平台宏（符合 R8）

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| zlib | 1.3.1 | 压缩 |
| sqlite3 | 3.49.1 | 数据库 |
| htslib | 1.24-r0 | BAM/SAM/CRAM 处理 |
| check | 0.15.2 | 上游单元测试框架 |

## 验证结果

```bash
# conan-verify 全门禁通过（G0-G4 + L2/L4/L5）
# 上游测试: 185/185 通过
# test_package: sider --version / --cite / 无参数 usage 3 项通过
```

## 注意事项

- package() 必须直接复制 build 产物（`self.build_folder/src/sider`），不能走
  `Meson.install()`——OHOS 上 install 重写 RUNPATH 会破坏 .codesign 签名导致
  运行时 EPERM。此经验可复用于其他 OHOS 下使用 meson install 的 CLI 包。
- 运行期动态库依赖（libdeflate 等）由 conanrun 环境 LD_LIBRARY_PATH 提供，
  不依赖二进制内嵌 RUNPATH。
---

**编译结束**: 2026-09-21 01:50
**最终状态**: published
