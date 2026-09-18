# geos 3.15.0 编译笔记（HarmonyOS PC · Conan cmake）

## 产物
`libgeos.so`、`libgeos_c.so`（C API）、`bin/geosop`（命令行几何运算工具）。

## 版本选择说明
3.15.0 为上游 stable 系列版本，按需求新增；与仓内已有的 3.13.0 / 3.13.1 /
3.14.1 并存、互不影响，已依赖旧版本的构建不受影响。
上游正式 tag 已核验：`refs/tags/3.15.0` = d0228513abb0c29c185443cf2bfb06c9281024b5
（git ls-remote 实测）。

## 关键适配
- 完全沿用 3.14.1 的配方（本仓 cmake 模板的标准 OHOS 工具链路径），无需源码补丁。
- geos 3.15.0 无外部 C 依赖（CMakeLists 中唯一 find_package 是内部 dist 模块）。
- 产物 `.so` 与 `bin/` ELF 经 `llvm-objcopy` 去旧签名后由 `binary-sign-tool` 自签
  （HarmonyOS XPM 拒绝未签名/被改动的 ELF）。

## 源码校验
- 官方 tarball（https://github.com/libgeos/geos/archive/refs/tags/3.15.0.tar.gz）
  sha256 = 134aaf78026f4311737e20ff1465cd31a48c4ca8858fb68e99d13ccd3d52753a
  （ghfast.top 与 gh-proxy.com 两个独立镜像下载交叉核验一致）。

## 状态
built（本地 `conan create` 通过，尚未上传制品仓）—— test_package 做真实几何断言
（构造 WKT、求交、判面积、缓冲区、错误回调），非仅链接成功。

### 对话 #1
- 上游 tag 3.15.0 已核验（d0228513abb0c29c185443cf2bfb06c9281024b5，git ls-remote 实测）。
- 配方完全沿用 3.14.1 cmake 模板，无需源码补丁（patches_applied 空）。
- configure: cmake -G Ninja 默认选项；make 全量编译 900+ 源文件。
- W3 本地 CI 通过（build_and_test.sh RC=0，1/1）；conan-verify 全门禁通过。
- 长构建超时预算本地提高至 10800s（不纳入 PR diff）。
---

**编译结束**: 2026-09-15 00:25
**最终状态**: built
