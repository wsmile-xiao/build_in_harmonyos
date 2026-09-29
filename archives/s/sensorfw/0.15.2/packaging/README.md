# packaging/ —— sensorfw 0.15.2

## 本目录为何存在

本包是 **Conan 2 配方（v3.0 归档格式）**：`conanfile.py` 从官方源码真实构建并封装，
制品以 Conan 包形式交付，引用为：

```
sensorfw/0.15.2@ohpcd/stable
package id 0b1ed271d5a43d09cfbf73bd802eb39db37e8ab9
```

`knowledge/ARCHIVE-SPEC.md` v3.0 已把 `packaging/` 与 `packaging/*.tar.gz`
列为**废弃/删除**（Conan 体系替代手动 tar 打包），因此本目录**不放**预编译
`*-ohos-aarch64.tar.gz`。

保留本目录的原因是一处**框架内部不一致**（已记入
`feedback/SKILL_FEEDBACK_c77a59c2.md`）：

- `scripts/ohc/finish.py:372-377`（submit 就绪预检）要求 `packaging/` **存在且非空**；
- `scripts/ohc/finalize_archive.py:108-112`（Step6 归档校验）把 `packaging/` 列为必填目录；
- 但同一条流水线的 `scripts/ohc/finish.py:85-95` 对 **v3.0 配方**（存在 `conanfile.py`）
  已明确跳过 legacy 的 `packaging/*.tar.gz` 分支。

仓内实践也如此：**81 个同时带 `conanfile.py` 的版本目录含有 `packaging/`**，
其中 51 例内容为 `README.md`、20 例为 `.packaged` 标记；
而**全仓 0 例提交 `*.tar.gz`**（该扩展名被 `.gitignore:143` 排除）。
本目录即对齐该实践。

## 交付物在哪

| 内容 | 位置 |
|---|---|
| Conan 配方与补丁 | `../conanfile.py`、`../conandata.yml`、`../patches/` |
| 消费者测试（含鸿蒙特有用例 `consumer.ohos.dlopen`） | `../test_package/` |
| 上游测试声明（CI 强制） | `../test_package/MANIFEST.yml` |
| 测试报告（含逐二进制明细、失败断言原文、复现命令） | `../reports/test-report.md` |
| 门禁证据 | `../reports/conan-verify-report.md`（G0–L5 逐门结论）、`../reports/pr-body.md` |

> 原始日志（`conan-create.log`、`w3-local-ci.log`、上游测试日志等）为**本地复现产物**，
> 按仓内惯例（12287 个包中仅 2 个提交 `reports/logs/`）**不随 PR 提交**；其关键原文已内联于
> `../reports/test-report.md`。

## 重新生成制品

```bash
CONAN_HOME=$HOME/.conan2 conan create ../ \
    -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
    -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 \
    --build=sensorfw/0.15.2
```
