# minia 3.2.6（HarmonyOS PC）

Minia 是基于 de Bruijn 图的短读长序列组装工具。此 Conan 配方从上游官方 `v3.2.6` tag 构建，并按该 tag 的 gitlink 固定下载 `gatb-core` 子模块提交 `99105b3b491d8dbd43e75ad390239b3279a0a8ab`。

## 使用

安装 Conan 包后可直接运行：

```sh
minia -in reads.fa -kmer-size 31 -abundance-min 2 -out assembly
```

查看完整参数：`minia`。该版本是命令行工具，不提供独立 Conan 运行时依赖；GATB core 已静态链接。

## 源码与许可

- 上游：<https://github.com/GATB/minia>
- 版本 tag：`v3.2.6`，commit `594d6e390841df82a28601ed810662bf0e463c7b`
- 许可：AGPL-3.0-or-later，许可证文本随上游源提供；GATB core 的 `LICENCE` 与 `THIRDPARTIES.md` 一并安装到包内 `licenses/gatb-core/`。
- Codeload 归档不包含 git 子模块内容，因此配方依据上游 tag 的 gitlink 下载并校验 GATB core 的精确提交归档。

## 验证

`conan create` 构建时运行上游 `test/simple_test.sh` 的四个组装场景。`test_package` 再以消费者环境调用已打包的 `minia`，运行固定的 X 图样例并断言生成六条 contig。2026-10-04 真机日志 `minia8879-create-r2.log` 中四个场景均打印 `PASSED`，`python3 test_minia.py` 之后 `CREATE_EXIT:0`。
