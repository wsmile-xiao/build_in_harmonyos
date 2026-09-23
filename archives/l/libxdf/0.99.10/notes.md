# libxdf 0.99.10 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-15
- 编译器: clang（OHOS SDK 26.0.0.18，`--target=aarch64-linux-ohos`）
- 目标平台: OHOS / armv8（Conan profile `ohos-aarch64`）
- 状态: built

## 编译步骤

1. 源码：`https://github.com/Yida-Lin/libxdf/archive/refs/tags/v0.99.10.tar.gz`（sha256 见 conandata.yml）。
   设备直连 github.com 不通，按经验把**官方 tarball 按 sha256 预置到共享 conan 下载缓存**
   （`~/tmp/ch/dlcache/s/<sha256>` + 同名 `.json` sidecar，references 同时登记官方 URL 与构建期镜像注入的 URL 形态），
   conandata.yml 仍只写官方 URL。
2. W0：`bash ci/scripts/preflight_check.sh libxdf/0.99.10`；依赖 `pugixml/1.16` 用
   `conan install --requires=pugixml/1.16 -r=ohpcd --build=never` 实测二进制可用（非 `conan list` 判断）。
3. 配方：CMakeDeps + CMakeToolchain；`cmake.configure()/build()/install()`（上游 CMakeLists 自带 install 规则）。
4. 消费者测试随 `conan create` 运行：`test_package/test.cpp` 自建最小合法 XDF 文件，
   经公开 API `Xdf::load_xdf` 解析并断言。
5. 门禁：`ohc-run.py conan-verify libxdf 0.99.10` → G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 走 vendored pugixml，配方的 `requires(pugixml)` 实际未被使用 | 上游判据是 `if(TARGET pugixml ...)`，而 Conan 生成的目标是 `pugixml::pugixml` | 补丁 `patches/0001-CMakeLists.txt.patch` 改判据与链接目标为 `pugixml::pugixml`（日志出现 `-- Using system pugixml` 佐证） |
| 2 | `source()` 下载失败（GitHub 与公共镜像站均超时） | 设备出网受限 | 预置共享下载缓存（见步骤 1）；缓存条目曾被上一次失败下载留下的 `.dirty` 标记连带清除，需先删标记再种文件 |
| 3 | 语言预检判 `env_unsupported`（mixed） | `docs/html`（生成的文档站点，144 个 HTML/JS 文件）被计入源码统计，nodejs 占比 87% | 实测主体为 `xdf.cpp/xdf.h`(C++) + CMake 构建；文档站点资产非源码主体，按 R47「辅助内容不算主体」继续适配，误判证据记录于此 |
| 4 | `make: jobserver mkfifo ... Operation not permitted` | HMDFS 不支持 mkfifo | 非阻塞警告，构建正常完成 |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：`if(TARGET pugixml ...)` → `if(TARGET pugixml::pugixml ...)`，
  `target_link_libraries(xdf PRIVATE pugixml)` → `pugixml::pugixml`。
  目的：使用平台制品仓提供的 pugixml，而不是编译上游 tarball 内的 vendored 副本。

## 依赖版本

- pugixml/1.16（平台已发布的预编译包，二进制实测可用）

## 上游测试

上游（Yida-Lin/libxdf）**未提供自动化测试**：`CMakeLists.txt` 无 `enable_testing()`/`add_test()`，
仓库无 `test/` 目录，`xdf.pro` 仅定义库目标。静态用例数 **N_static = 0**。
因此按赛事口径「上游确无测试时才允许消费者测试补位」，由 `test_package` 承担真实测试。

## 验证结果

```bash
# 设备（CONAN_HOME=~/tmp/ch/home-glm41-libxdf）
python3 scripts/ohc-run.py conan-verify libxdf 0.99.10
# → G0 PASS / G1 PASS / G2 PASS / G3 PASS / G4 PASS / L2 L4 L5 PASS

# 消费者测试（conan create 内运行，reports/conan-create.log）
ok  : load_xdf returns 0 for a valid XDF file
ok  : one stream parsed
ok  : stream name parsed from header XML
...
ok  : missing file returns 1
ok  : bad magic returns -1
libxdf consumer test: all checks passed
```

消费者测试：1 个消费者程序（`test_package/test.cpp`），17 项断言全部通过，
覆盖 `Xdf::load_xdf` 成功路径（流元数据 / 通道描述 / 采样值 / 时间戳）与两个失败路径（返回 1 / -1）。

## 注意事项

- 本包为纯客户端解析库：编译产物 `libxdf.a` + `include/xdf.h`，无命令行工具，故无 `commands.json`。
- 上游内置的 `pugixml/`、`smarc/` 目录保持原样（smarc 为上游自带的滤波实现，属本库源码的一部分）。

---

**编译结束**: 2026-09-16 00:12
**最终状态**: built
