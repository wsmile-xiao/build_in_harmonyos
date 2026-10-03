# sofa 20231011-also-called-release-19 适配笔记

## 编译环境

- 构建系统: custom（上游无 CMake/autotools 入口，以 Conan 配置的 C 编译器直接编译）
- 编译日期: 2026-10-02
- 编译器: clang（真机通过 `tools.build:compiler_executables` 注入，配方不依赖裸 `$CC`）
- 状态: built（首轮仅完成未提交工作树，真机 rule4 门禁待 HMBS 后台执行）

## 上游确认

- 软件：IAU Standards of Fundamental Astronomy (SOFA) C Library
- 上游版本：2023-10-11，即第十九版（"also called release 19"），任务版本号如实取为 `20231011-also-called-release-19`
- 上游主页：https://www.iausofa.org
- 源码包：https://www.iausofa.org/s/sofa_c-20231011tar.gz（官方 Unix tarball，经 HTTPS 获取）
- SHA-256：`d9c10833cae8b4d9361a0ffda31ec361fd1262362025bec4d4e51a880150ace2`（与 conan-center-index sofa/20231011 同文件交叉确认）
- 许可证：SOFA Software License（文本位于源码 `sofa.h` 文件头注释，配方提取为 `licenses/LICENSE`）

## 编译步骤

1. `get()` 下载解压（`strip_root=True`），源码定位兼容 `20231011/c/src` 与 `c/src` 两种布局。
2. 以配置编译器逐个编译 `c/src/*.c`（除自检程序 `t_sofa_c.c` 外）为 `.o`，静态归档为
   `libsofa_c.a`（`shared=True` 时链接为 `libsofa_c.so`），编译期打开 `-fPIC`（shared 或 fPIC 选项）。
3. 安装头文件 `sofa.h`、`sofam.h` 到 `include/`，库文件到 `lib/`。
4. 上游测试：在 `build()` 内按上游 makefile 的 check 语义编译 `t_sofa_c.c` 并运行
   `./t_sofa_c`，输出落盘 `t_sofa_c.log`，以退出码 + `t_sofa_c validation successful`
   为通过判据，通过后打印 `HMBS_UPSTREAM_TEST_RESULT` 标记；失败则中断构建。

## 上游测试盘点

- 上游仅注册 1 个自检程序：`20231011/c/src/t_sofa_c.c`（`main` 内依次调用约 200 个
  `t_*` 例程验证函数，每个例程以 `viv`/`vvd` 按 1e-12 量级容差比对参考值；全部通过时
  仅打印 `t_sofa_c validation successful`，失败才逐项打印 `... failed ...`）。
- 上游 vendor makefile 提供 `check` 目标（编译并运行该程序）；配方未调用 vendor
  makefile，而是在 `build()` 内复现等价动作，因此 `upstream_test_in_build: true`。
- 计数口径：`upstream_test_total: 1`，方法 `auto`（单一自研 testbed 程序，无
  ctest/gtest/autotools 注册表可数）。

## test_package 设计

- `test_sofa.c` 以消费者视角调用 4 组真实 API（均为链接与数值双重验证，任一失败即
  非零退出）：
  - TC1：`iauCal2jd` + `iauJd2cal` 往返（2023-10-11，校验 MJD 零点与日期往返一致）；
  - TC2：`iauEpb2jd` + `iauEpb` 往返（Bessel 纪元，容差 1e-9）；
  - TC3：`iauDat`（2023-10-11 的 TAI-UTC，状态为 0 且落在 [30, 40] 秒区间）；
  - TC4：`iauEra00`（J2000 地球自转角落在 [0, 2π) 区间）。
- 通过 CMake + CMakeDeps 链接 `sofa::sofa`，`test()` 运行二进制并打印
  `HMBS_TEST_PACKAGE_RESULT`（discovered=4/passedCount=4）与
  `HMBS_UPSTREAM_TEST_RESULT`（build 期已门禁，通过才进入 test 阶段）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码包顶层目录名不确定（`strip_root` 后 `c/src` 的父路径未知） | 官方 tarball 顶层为 `20231011`，但 conan-center 配方却按 `<src>/<version>/c/src` 取址，两种布局说法并存 | 配方按候选路径逐个探测 `sofa.h` + `t_sofa_c.c`，兜底 glob 全树定位 `t_sofa_c.c` |
| 2 | 上游 URL 在 conan-center 为 `http://`，本仓要求 HTTPS | 旧配方年代写法 | 实测 `https://www.iausofa.org/s/sofa_c-20231011tar.gz` 可访问，改用 HTTPS，保留同一文件与 SHA-256 |
| 3 | `package_info` 的 `libm` 在 OHOS 是否需要 | 上游所有链接均带 `-lm`；conan-center 仅对 Linux/FreeBSD 声明 | 按 R32 风格对 `("Linux", "FreeBSD", "OHOS")` 声明 `m`，真机若提示多余/缺失再按实测收敛 |

## 依赖版本

无外部依赖（仅系统 `libm`，由工具链提供）。

## 验证结果

```bash
# 首轮仅完成工作树；以下待 HMBS 后台真机预检执行后回填：
# conan create archives/s/sofa/20231011-also-called-release-19 \
#   -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
#   --build=missing -tf=test_package
# 预期：上游 t_sofa_c 1/1 通过；消费者 test_sofa 4/4 通过。
```

## 交付物

首轮无产物（工作树未提交）。

## 注意事项

- 本轮严禁 commit/push/建 PR；修改完成后即结束本轮，由 HMBS 后台做完整真机验证。
- 若真机 `t_sofa_c` 出现个别例程失败，需按 `viv`/`vvd` 的 `... failed ...` 行定位
  具体函数与容差，不删除测试调用；平台相关失败在 MANIFEST `gaps` 中如实审计。
- `package_type = "library"` 配合 shared 选项；sofa 非系统同名库，无需 R26 强制静态。
