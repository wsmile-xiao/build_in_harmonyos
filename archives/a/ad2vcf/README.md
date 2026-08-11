# ad2vcf

## 简介

ad2vcf extracts allelic depth information from a SAM stream and adds it to a corresponding single-sample VCF file.

## OHOS 适配

- 上游使用 Makefile，recipe 构建单个命令行程序 `ad2vcf`。
- 依赖 `biolibc/0.2.7` 和 `libxtend/0.2.1`。
- OHOS 构建期生成 `sysexits.h` 和 `sys/param.h` 兼容头。
- OHOS 下显式映射 `strlcpy/strlcat` 到 libxtend 的 `xt_strlcpy/xt_strlcat`。
- OHOS 可执行文件在 package 阶段使用 `binary-sign-tool` 签名。

## 依赖

- biolibc/0.2.7
- libxtend/0.2.1

## 功能验证

test_package 运行 `ad2vcf --version`，并使用上游 `Test/test.vcf`、`Test/test.sam`、`Test/test-ad-correct.vcf` 执行正向 fixture 对比。

