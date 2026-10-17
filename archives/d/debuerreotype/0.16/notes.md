# debuerreotype 0.16 适配笔记（HarmonyOS PC · 纯 Bash 脚本应用打包）

## 定位

- debuerreotype 是 debuerreotype/debuerreotype 的可复现、基于 snapshot.debian.org 的
  Debian rootfs 构建器（一组自包含 Bash 脚本，主要面向 Docker 镜像制作）。
- **纯 Bash 应用，无编译产物** → 走脚本打包路径（build_system: none），先例：
  archives/d/dehydrated/0.7.2、archives/l/lzop/1.04（工具 + 无上游单元测试 markers 形态）。

## 关键适配

- **零补丁**：上游脚本在 OHOS 运行时无需修改，`patches_applied: []`。
- **自检即验证**：build() 做两步——`bash -n` 语法自检（全部 `scripts/debuerreotype-*`）
  + `debuerreotype-version` 冒烟（真实执行脚本：source `.constants.sh`、走 getopt
  选项解析、读取 VERSION），并 grep 核对 `0.16` 输出。
- **test_package**：消费者视角 5 项断言（test_debuerreotype.sh）——入口脚本在 PATH、
  已安装入口 `bash -n`、version 实执输出 0.16、`--help` 输出核验（`debuerreotype-version
  --help` 打印 `debuerreotype version 0.16`，因该脚本以空 usage 字符串 source
  `.constants.sh` 故无 `usage:` 字样，另以 `debuerreotype-tar --help` 覆盖 `usage:`
  输出）、helper（`.constants.sh`）与 `VERSION` 随包安装。
- 上游无任何单元测试套件（见下方 discovery），`upstream_tests_exist: false` 如实声明，
  真机输出 `HMBS_UPSTREAM_TEST_RESULT status:"no_tests" discovered:0 executed:0`。

## 安装布局

- `bin/debuerreotype-*`（11 个入口，755）+ `bin/.*.sh`、`.slimify-*`、`.tar-exclude`
 （入口运行时 source 的 helper，必须随包）。
- `VERSION` 置于包根（`bin/../VERSION`），保持上游 `_version()` 的
  `"$scriptsDir/../VERSION"` 读取路径可用。
- `licenses/LICENSE`（MIT），`share/doc/debuerreotype/`（README、Dockerfile、
  docker-run.sh、examples/）。

## 风险点

| # | 风险 | 处置 |
|---|------|------|
| 1 | `.constants.sh` 用 GNU getopt `--long` 做选项解析，OHOS toybox getopt 若不支持会使 `--version/--help` 实执失败 | 真机预检直接验证；若失败再视日志决定是否补 GNU getopt 依赖或收紧冒烟范围，不在未实测前预设补丁 |
| 2 | 脚本 shebang 为 `#!/usr/bin/env bash`，依赖 PATH 含 hnp bash | profile 与 hmbs 已将 `/data/service/hnp/bin` 前置到 PATH，conanrun env 下 `command -v` 可解析；测试用显式 bash 回退路径 |
| 3 | `readlink -vf` 在部分精简 readlink 上行为差异 | version/help 路径实测覆盖；若真机失败按日志修 |
| 4 | 上游 CI（debootstrap + Docker + snapshot.debian.org 公网）不可移植 | 已审计声明 no_tests，不强行移植；功能验证只做脚本可执行性与选项解析，不做真实 rootfs 构建（需 root/特权/公网） |

## 上游测试 discovery（NO_UPSTREAM_TESTS）

- **discovery.status**: EVIDENCE_COMPLETE
- **结论**: 上游（debuerreotype/debuerreotype，tag 0.16）不发布任何可运行单元测试套件。
- **已检查入口/证据**:
  1. tag 0.16 归档全量文件清单（50 项）：VERSION、LICENSE、README.md、Dockerfile、
     docker-run.sh、generate-github-actions.sh、examples/（5 个用法示例脚本）、
     scripts/（11 个 `debuerreotype-*` 入口 + `.constants.sh`、`.apt-version.sh`、
     `.snapshot-url.sh`、`.debian-mirror.sh`、`.dpkg-arch.sh`、`.fix-apt-comments.sh`、
     `.gpgv-ignore-expiration.sh`、`.slimify-excludes`、`.slimify-includes`、
     `.tar-exclude`、`.debootstrap-scripts/`）、`.validate-*.sh`（4 个）、
     `.github/workflows/ci.yml`——无 tests/、test/、Makefile、CMakeLists、meson.build。
  2. 全树 `find -name '*test*'`：仅命中 ci.yml 内核对 testing 发行版（stretch/sid）的
     Debian 套件名字面引用，无测试文件。
  3. 源码无 `TEST(`/`TEST_F`（gtest）、`def test_`（pytest）、`TESTS`/`check_PROGRAMS`
    （automake）、`ctest` 注册。
  4. `.github/workflows/ci.yml` 的 test 矩阵全部调用 `.validate-debian.sh` 等脚本做
     debootstrap + Docker + snapshot.debian.org 端到端可复现性校验（固定 TIMESTAMP 的
     SHA256 比对 + noble/jammy smoke），需 root、debootstrap、Docker daemon、公网，
     在 OHOS 上不可运行。
- **替代验证（配方内已执行）**: `bash -n` 语法自检 + `debuerreotype-version` 实执冒烟
  （VERSION 硬编码为 `0.16`，`--version` 走真实 getopt 解析路径）。
- **证据**: tag 0.16 归档
  `https://github.com/debuerreotype/debuerreotype/archive/refs/tags/0.16.tar.gz`
 （SHA256=0ace5b5ccb473a1ef3adcd82c3ae474b2fea7fc1c99cf6682218e58c34a5acfa）。

## 编译步骤

```bash
conan create archives/d/debuerreotype/0.16 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 配方内 build()：纯 Bash 脚本无编译，仅做自检
cd $source_folder && bash -n scripts/debuerreotype-version \
  && for s in scripts/debuerreotype-*; do bash -n "$s"; done \
  && bash scripts/debuerreotype-version | grep -q 0.16
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/debuerreotype-* | 11 个入口脚本（755） |
| bin/.*.sh、.slimify-*、.tar-exclude | 运行时 source 的 helper |
| VERSION | 包根版本文件（供 `_version()` 读取） |
| licenses/LICENSE | MIT 许可证 |
| share/doc/debuerreotype/ | README.md、Dockerfile、docker-run.sh、examples/ |

## 注意事项

- R38：package_type="application" 且产出到 bin/ → commands.json 已声明（binary: false，脚本应用）。
- R26：纯脚本无 .so 产物，系统同名库隔离不适用。
- 真实 rootfs 构建需 root/debootstrap/Docker/公网（用户态使用场景），本包交付可运行脚本与文档；
  test_package 验证脚本可执行性与选项解析，不做真实 Debian 构建与网络请求。
- CI 跑后须核验 conandata.yml 与 HEAD 逐字节一致（mirror-fallback 原地改写需恢复）。

---

**编译结束**: 2026-09-12
**最终状态**: built
