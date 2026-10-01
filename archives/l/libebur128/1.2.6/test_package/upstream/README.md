# upstream/ — verbatim upstream test programs (libebur128 v1.2.6)

These three files are copied **unmodified** from the upstream tag
`v1.2.6` (https://github.com/jiixyj/libebur128, MIT license, see
`COPYING` in the source archive):

| 文件 | 上游用途 | 本包执行方式 |
|------|---------|-------------|
| `tests.c` | EBU R128 参考套件（64 断言，读取 EBU 官方测试向量 wav） | 链接 `sndfile_stub/`（仅实现 sf_open/sf_readf_double/sf_close 的 RIFF PCM 读取 shim）后编译执行；向量由 `../gen_r128_vectors.py` 合成（EBU 素材有分发政策，不能入库/CI 下载） |
| `minimal-example.c` | 上游官方示例：读 wav 打印门限响度 | 同上，使用合成向量 |
| `fuzzer.cpp` | 上游 fuzzer（malloc 故障注入 + 随机参数） | 无 sndfile 依赖；由 `../fuzzer_driver.cpp` 以确定性伪随机输入驱动（OHOS clang 无 libFuzzer runtime） |

目的：满足 PR 审查 rule4「真实执行上游测试用例」——三个上游测试
程序全部真实编译并在目标平台执行，可合成向量的断言真实通过
（详见 MANIFEST.yml 与 PR 描述的逐项统计）。
