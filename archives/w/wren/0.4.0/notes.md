# wren 0.4.0 适配笔记

## 编译环境
- 构建系统: makefile（premake 生成，projects/make/）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4（ohos-aarch64 profile 交叉编译）
- 状态: built（conan-verify 8 门禁通过，可标 published）

## 编译步骤

1. `init-build wren 0.4.0 --url=https://github.com/wren-lang/wren/archive/refs/tags/0.4.0.tar.gz`
   - GitHub 直连超时，经 ghfast.top 镜像下载官方 tag tarball（sha256 核验一致）
   - 注意: tarfile.extractall 在该机未完整解压（仅顶层 8 文件），已手动重建 orig/work 双轨
2. 语言预检: `lang-preflight` → task=cpp 兼容族，detected=c，通过
3. 编译: `make -C projects/make config=release_64bit`
   - 产物: lib/libwren.a、lib/libwren.so、bin/wren_test
4. 上游测试: `python3 util/test.py` → **862/862 通过（3855 expectations）**
5. 配方: `conan-init` 生成 → 改写为 Makefile 型配方（GnuToolchain + make -C projects/make）
6. 验证: `conan-verify` → G0-G4 + L2/L4/L5 全 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | 网络策略阻断 github.com | 经 ghfast.top 镜像下载官方 tag tarball，sha256 与官方一致 |
| 2 | 上游测试 498/892 误判失败 | 直接驱动 wren_test 未按 expect 注释判定 | 改用官方 util/test.py 运行器（862/862 全过） |
| 3 | conan create 报 cpp_info.requires 错误 | conan 2.x requires 仅允许组件引用，libm 是系统库 | 改为 cpp_info.system_libs = ["m"] |
| 4 | W3 JC5 失败（.ci-trigger） | 其他库 util-linux-login 的 HEAD 基线文件不在 JC5 白名单 | 按基线隔离规程：临时 git rm --cached → 复验 W3 → 无条件恢复（blob/哈希核验干净） |
| 5 | 冗余补丁 0001-0003 | 重建源码树时点文件一度缺失，refresh-patch 误生成整文件补丁 | 从 tarball 恢复 orig 点文件并核验哈希一致后删除冗余补丁 |

## 源码修改

无。wren 0.4.0 官方源码在 OHOS aarch64 下原生编译通过，无需补丁。

## 依赖版本

- 无 Conan 依赖（仅系统 libm）
- 工具链: clang 15.0.4 / GNU Make 4.4.1 / Conan 2.29.1 / Python 3.12.9

## 验证结果

```bash
# 上游测试（release_64bit）
python3 ./util/test.py
# => All 862 tests passed (3855 expectations)

# 配方干净构建验证
conan create archives/w/wren/0.4.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# => PASS（conan-verify 8 门禁全过，test_package 消费者测试通过）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | 3.0 KB | Makefile 型 Conan 配方（GnuToolchain） |
| conandata.yml | 384 B | 官方源 + sha256 核验 |
| test_package/ | - | 消费者测试（真实调用 wren VM API） |
| packaging/wren-0.4.0-libs.tar.gz | 380 KB | 构建产物归档（libwren.a/.so） |
| packaging/wren-0.4.0-headers.tar.gz | 26 KB | 公共头文件归档（wren.h/wren.hpp） |

## 注意事项

- wren 无 `make install` 目标，配方 package() 手工复制 lib/ 与 src/include/。
- 上游测试入口是 `util/test.py` 而非 `make check`。
- 该机 GitHub 直连不可达，conan-verify 已内置 E017 镜像注入（ghfast.top）自动处理。
---

**编译结束**: 2026-09-08 22:13
**最终状态**: built
