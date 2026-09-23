# tinyxxd 1.3.16 适配笔记

## 编译环境
- 构建系统: 上游 Makefile；本仓库直接编译（custom）
- 编译日期: 2026-09-15
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 状态: built

## 版本与源码
- 任务版本 `1.3.16` 对应上游 git tag `v1.3.16`（上游 tag 带 `v` 前缀）。
- 源码：`https://codeload.github.com/xyproto/tinyxxd/tar.gz/refs/tags/v1.3.16`
  （官方 GitHub codeload 主机；同一归档的 `github.com/.../archive/...` 作为备份 URL，
  两者字节一致）sha256 `f74a3cbcdd3166f0f966f97ad483a60a34b53a09abd9ba63783c0958640ca9d9`。
- 说明：`conan create` 期间 `github.com` 在本机网络不可达（超时），故 `sources.url`
  采用官方 `codeload.github.com`（仓库内已有大量先例，且不在 PF7 镜像黑名单内）。

## 编译步骤

上游 `Makefile` 的 `tinyxxd` 目标就是一条编译命令，但它的 `CFLAGS` 带 `-Werror`，
`test` 目标还会下载 ViM 的 `xxd` 并构建 ASan 版本。为避免这些 CI 不可复现的依赖，
直接编译：

```sh
clang -std=c11 -D_GNU_SOURCE -fstack-protector-strong -O2 main.c -o tinyxxd
```

`package()` 安装 `bin/tinyxxd`（0755）、`share/man/man1/tinyxxd.1`、`licenses/LICENSE`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make test` 不可在 CI 复现 | 需要联网下载 ViM 的 xxd 作对照，并用 `-fsanitize=address,undefined` 构建 | 改为复现 `testfiles/` 的自包含脚本与 `make test` 中不依赖 xxd 的用例 |
| 2 | `Makefile` 的 `-Werror -Wconversion ...` 在 clang 上易炸 | 上游面向 gcc 调优 | 直接编译，不用上游 `CFLAGS` |
| 3 | 命令行工具需要声明 | 产物含 `bin/` | 软件级 `commands.json`，`package_type="application"`（R38） |
| 4 | 上游测试脚本用 `/tmp`（OHOS 只读） | `test_c0.sh` 写 `/tmp` | 测试在可写的临时目录运行（TMPDIR 或 `$HOME`） |

## 源码修改

无补丁（`patches/` 为空）。

## 依赖版本

无外部依赖。

## 验证结果

```bash
./tinyxxd -h                     # stdout 含 "Usage"
./tinyxxd -Z                     # stderr 含 "Usage"，rc != 0
./tinyxxd -i -b XXDfile          # 与 test13 期望一致
./tinyxxd -c 0 -ps hello.bin     # 68656c6c6f20776f726c64
./tinyxxd sample.bin > dump.hex
./tinyxxd -r dump.hex            # 与 sample.bin 相同
# 16 组上游用例 + 2 组消费者检查全部通过
```

`conan create tinyxxd/1.3.16` 退出码 0。

## 注意事项

- 上游 tag 带 `v` 前缀（v1.3.16）；Conan 版本按平台任务填 `1.3.16`。
- 工具类型必须带 `commands.json`，否则 CI L0k 拦截。
