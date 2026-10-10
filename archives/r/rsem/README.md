# rsem

RSEM (RNA-Seq by Expectation-Maximization) — 从 RNA-Seq 数据进行准确转录本
定量的命令行工具套件，内含捆绑的 samtools 1.3（含 htslib 1.3）与裁剪版
header-only boost 1.55，Perl 前端脚本需要运行时 perl。

## Versions

| Version | Status |
| --- | --- |
| 1.3.3 | published |

Homepage: https://github.com/deweylab/RSEM

## 适配要点（鸿蒙PC / aarch64-linux-ohos）

- 保持 `-std=gnu++98`（源码依赖 C++98 隐式 istream->bool 转换）
- 捆绑 boost 1.55 math/tuple 需要 fusion 兜底补丁（libc++ C++98 下 `<tuple>` 为空）
- samtools-1.3 内嵌 configure 在 HMDFS 上 config.status 失败，改为手工生成
  config.mk/config.h
- 唯一外部编译依赖：zlib（conan 制品仓 zlib/1.3.1）
