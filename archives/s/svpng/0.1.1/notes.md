# svpng 0.1.1 适配笔记

## 编译环境
- 构建系统: 无（单头文件库，header-only）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 / clang++（OHOS aarch64 profile：ci/conan/profiles/ohos-aarch64）
- 状态: published

## 源码获取
- 官方上游: https://github.com/miloyip/svpng (tag v0.1.1)
- 源码包: svpng-0.1.1.tar.gz
- SHA-256: e81010fbd82c30bac21d3fa7fd08f576522086cac65aa35503413d9bf3842689
- GitHub 直连超时，本地经 codeload.github.com 官方归档 CDN 下载，与 ghfast.top 镜像包逐字节一致；conandata.yml 提交官方 URL（R39/PF7），CI E017 自动注入 ghfast.top 镜像并还原。

## 适配说明
- svpng 是 Milo Yip 的极简 PNG 编码函数（svpng.inc 单头文件，MIT），无 configure/Makefile/CMake，无依赖。
- conanfile.py 采用 header-library 类型：source() 拉取官方 tag 归档，package() 将 svpng.inc 装入 include/、LICENSE 装入 licenses/。
- build() 中以 OHOS 工具链（self.conf 读取，R33）编译上游 example.c，作为头文件在 OHOS 平台可编译的适配断言。
- conan-verify G1 门禁要求 conanfile.py 显式包含 build()/export_sources()/apply_conandata_patches 方法签名；空补丁时 apply_conandata_patches 安全无操作。

## 上游测试（example.c，双口径）
- 源码声明独立用例：test_rgb（生成 256x256 RGB PNG）、test_rgba（生成 256x256 RGBA PNG），共 2 个，均由 main() 顺序调用。
- 实际编译运行：clang -std=c99 -O2 -Wall -Wextra example.c -o example，cwd=/storage/Users/currentUser/tmp/svpng-test-run，退出码 0。
- 输出与官方仓库参考图逐字节一致（rgb.png sha256=eab46a2b...，rgba.png sha256=e4c4b46d...），确定性编码验证通过。
- 通过率：2/2（source_declared=2, configured_executable=2, executed_passed=2, failed=0, unrun=0）。

## 鸿蒙专项测试（本轮新增）
- test_package/test_ohos.c：OHOS aarch64 专项，运行期解析 svpng() 输出 PNG 的 IHDR/IDAT/IEND 块，逐项断言宽高 32x32、位深 8、颜色类型 RGB=2/RGBA=6、压缩/滤波/隔行=0、IEND 长度=0。
- conan create 内 ctest 实测 2/2 Passed（test_svpng + test_ohos），非空壳、真实结构级断言。

## 消费者验证
- test_package/test.c：仅通过安装包导出的公开头文件 svpng.inc 与公开 API svpng()，生成 32x32 RGBA PNG 并断言 PNG 签名、文件大小；随 conan create 实际运行并通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时（urlopen timeout） | 本环境无法直连 github.com | 用官方 codeload CDN / ghfast.top 镜像本地拉包，conandata.yml 仍提交官方 URL，CI 自动镜像 fallback |
| 2 | conan-init 生成 autotools 模板 | 模板按构建系统猜测，svpng 无构建系统 | 重写为 header-library 配方（参考 stb_image/debugbreak 先例） |
| 3 | G1 配方完整性失败 | conanfile.py 缺 build()/export_sources()/apply_conandata_patches | 补全方法；build() 编译上游 example.c 做真实适配断言 |
| 4 | preflight PF7 拦截：conandata.yml 残留 gh-proxy.com 镜像前缀 | conan-verify 的 E017 镜像注入把 url 改写为带镜像前缀的列表且未被还原，随 commit 提交（R39 违规；CI 会自动加镜像 fallback，配方文件不得手写镜像） | 恢复 conandata.yml 为官方单 URL 并重提交复验；提交前核对 conandata.yml 无 gh-proxy/ghfast 前缀 |
| 5 | pre-commit L0k 误报 CLI 缺 commands.json | hook 用朴素子串匹配 "bindirs"，header-only 配方 `cpp_info.bindirs=[]` 触发误判；svpng 为纯库不得伪造 commands.json | 移除 package_info 中冗余 bindirs/libdirs 赋值（header-library 默认即空），注释亦避免出现该子串 |

## 验证结果

```bash
# 上游测试
clang -std=c99 -O2 -Wall -Wextra example.c -o example && ./example   # exit 0
cmp rgb.png $SRC/rgb.png && cmp rgba.png $SRC/rgba.png                # IDENTICAL

# conan-verify（G1-G4 + L2/L4/L5 全 PASS）
python3 scripts/ohc-run.py conan-verify svpng 0.1.1                   # exit 0
# conan create ctest: 2/2 Passed（test_svpng + test_ohos）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 配方（R26/R33/R34 合规） |
| conandata.yml | 官方 tag 源 + sha256（R39 合规） |
| test_package/test.c | 消费者验证（公开 API svpng()） |
| test_package/test_ohos.c | 鸿蒙 aarch64 专项测试（结构级断言） |
| test_package/CMakeLists.txt | 双测试目标 |
| test_package/MANIFEST.yml | 上游/专项/消费者测试声明 |

## 注意事项
- 库类型（纯头文件），无 CLI，不创建 commands.json（R38 不适用）。
- 无系统同名库冲突（R26 不需要静态配置）。
- svpng 输出未压缩 PNG，IHDR 颜色类型 RGB=2/RGBA=6，位深固定 8。
---

**编译结束**: 2026-09-19 22:06
**最终状态**: published
