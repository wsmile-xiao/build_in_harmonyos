# libblzf 3.6.1 OHOS 适配记录（本地迭代版本）

## 一、归档性质

- **本归档为本地迭代版本 3.6.1**：上游 liblzf 无 3.6.1，源码仍为 liblzf 3.6 tarball。
- **由来**：main 已于 2026-09-23 通过 `e681381b70`（【积分赛】feat(liblzf): 3.6 适配 HarmonyOS PC）
  合并了 `archives/l/liblzf/3.6/` 的完整 Conan 配方（conanfile.py + conandata.yml + test_package，
  含 CI 下载超时规避的镜像优先 URL 列表）。为避免与 main 已发布归档冲突并承载本轮
  Conan 配方化补全工作，本 PR 迭代版本号至 3.6.1，作为独立归档提交。
- **配方基线**：conanfile.py / conandata.yml / test_package 与 main 上已验证的 3.6 配方保持一致
  （仅版本号与说明更新），确保 CI 通过率与 3.6 相当。

## 二、源码

- 源码包：`liblzf_3.6.orig.tar.gz`（Debian pool，任务指定上游 URL）
  - 与官方发布包 `http://dist.schmorp.de/liblzf/liblzf-3.6.tar.gz` 逐字节相同（57120 字节，
    sha256 `9c5de01f7b9ccae40c3f619d26a7abec9986c06c36d260c179cedd04b89fb46a`）。
  - **CI 下载超时规避**：conandata.yml 使用镜像优先的 URL 列表——清华 TUNA Debian 镜像优先，
    deb.debian.org 兜底，官方站 dist.schmorp.de 在 worker 上不可达（worker 网络受限，仅部分域名放行）。

## 三、构建配置

- 构建系统：Autotools（configure.ac + 预生成 configure + 手写 Makefile.in，非 automake/cmake/meson）。
- 仅产出静态 `liblzf.a`（无 .so），天然无 R26 系统库污染风险。
- 编译器/SHELL/TMPDIR 走 HMBS 注入 + build 域 env 修正（bwm/0.6.3 同款），不传 --build/--host（R15）。

## 四、测试

- 上游无测试套件（18 项发布包审计：无 tests/ 目录、无 check/test 目标），按 no_tests 口径输出 HMBS 标记。
- test_package 消费者测试（真实调用库 API + 真实执行 CLI）：
  - 5 个 C API 用例（ctest）：roundtrip_text / roundtrip_binary / roundtrip_large /
    corrupt_einval / small_out_e2big（压缩往返 + EINVAL/E2BIG 错误码）
  - 1 个 CLI 用例（ctest）：bin/lzf 压缩解压往返 + 垃圾输入反向证伪
- 断言总数：9。

## 五、验证记录

- 本地验证：conandata URL 可达、sha256 与镜像包一致（9c5de01f…b46a）。
- CI 验证：由 PR 流程执行 `conan create archives/l/libblzf/3.6.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`（待 CI 结果回填）。
