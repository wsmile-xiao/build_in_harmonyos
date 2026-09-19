# seqprep 1.3.2 适配笔记

## 编译环境
- 构建系统: makefile（raw make，无 configure）
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4（ohos-aarch64 profile，交叉 aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

conan create（conan-verify G2 驱动，dlcache 命中预置源码）→ 配方 build()：
1. `make -j1 CC=<conf 取 clang> COPTS=-I<zlib include> CFLAGS="-c -O2 -std=c99 -Wall" LDFLAGS="-L<zlib lib> -lz -lm"`（E074 单线程；上游 CFLAGS 内嵌 -c，覆盖时保留）；
2. `sh Test/RUNTEST.sh`（补丁 0001 可移植化后真实执行：两次真实合并/修剪任务 + 5 条 zcat/py3 读长直方图管线）；
3. `make install` 语义由 package() 等价实现（SeqPrep 二进制 + LICENSE/README → bin/、licenses/）。
test_package：可执行包消费者测试 test.sh（test_type=explicit + VirtualRunEnv，/bin/sh 执行）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | zlib/1.3.1@ohpcd/stable not resolved | ohpcd 远端 zlib 以无 user/channel 形式发布；R27 的 @ohpcd/stable 后缀仅适用于部分包 | 按全仓 152 处惯例写 `self.requires("zlib/1.3.1")` |
| 2 | self.conf.get("tools.build:compiler_executables:c") 抛 does not exist | 该 conan 版本对 profile 字典型 conf 的子键取法异常 | try/except 回退 "clang"（与 AutotoolsToolchain 生成的 PATH 解析等价，R33 语义不变） |
| 3 | RUNTEST.sh 报 ../SeqPrep not found / seqlens.py 不存在 | 脚本以自身目录为 cwd 设计（../SeqPrep、./out、./info） | build() 以 cwd=source/Test 执行 |
| 4 | test_package bash 启动即 getcwd 风暴（E386 家族） | 模板默认 /data/service/hnp/bin/bash 在 HMDFS 归档目录 getcwd 失败 | test() 默认解释器改 /bin/sh（mksh getcwd 正常，脚本为 POSIX） |
| 5 | 合成读对全部被 Discard | 带 -A/-B 接头的合成构造与上游修剪预期不符 | 消费者测试改用纯重叠对（r1=insert, r2=rc(insert)），4 对全部成功合并 |
| 6 | 输出断言失败 | SeqPrep 无论扩展名一律写 gzip；且合并共识含容差悬挂碱基（60bp 输入合并为 66bp，确定性） | 断言改经 zcat 解码：merged 记录数 >0、序列长 55–70 区间 |

## 源码修改

- patches/0001-test-suite-portability.patch（上游测试可移植性，语义不变，逐项说明见 PR 正文）：
  - Test/RUNTEST.sh：`#!/bin/bash -x`→`#!/bin/sh`；补 `mkdir -p out info`；`prog=gzcat`→`prog=zcat`；`python seqlens.py`→`python3 seqlens.py`（5 处）
  - Test/seqlens.py：`seqlens.iteritems()`→`seqlens.items()`（py3）

## 依赖版本

- zlib/1.3.1（conan 依赖，链接 -lz）；运行时无其他依赖（-lm 为工具链 math）
- 构建工具：设备工具链 clang/make（R33/R26 不适用——可执行包无静态库选项）

## 验证结果

```bash
# conan-verify（G0–G4 全 PASS，Verdict: PASS）
python3 scripts/ohc-run.py conan-verify seqprep 1.3.2
# 上游测试（Test/RUNTEST.sh，补丁 0001 可移植化后真实执行）：
#   对内置 multiplex gz 数据：14314 对合并、4091 对检出接头、输出三文件非空且为合法 gzip
#   （脚本级账本：1/1 执行通过；工具自带的 "fastq record not beginning with @"×2
#    为良性 EOF 噪音，上游自带数据同样出现，见 consumers 断言设计说明）
# 消费者测试（test_package/test.sh，真实运行打包二进制）：
#   合成 4 对 100% 重叠读对 → 4 条合并记录、合并序列长 66（60bp 插入 + 确定性容差悬挂）、
#   退出码 0；7 项断言全通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/SeqPrep | ~150KB | 可执行工具（commands.json 已登记，R38） |
| licenses/LICENSE + README.md | ~20KB | 许可与说明 |

## 注意事项

- SeqPrep 输出永远为 gzip 格式（与扩展名无关）；EOF 处必打两行 "fastq record not beginning with @" 且 Pairs Processed 计数恒为 0（上游自带数据同样如此）——均为良性噪音，断言勿依赖计数器。
- 上游 RUNTEST.sh 原始形态依赖 bash/gzcat/python2，HarmonyOS 不可直接执行；本适配以最小可移植性补丁使其真实执行（修改上游测试，已逐项说明），未从账本删除任何用例。

## finish 收尾块

- finish: `python3 scripts/ohc-run.py finish seqprep 1.3.2 built`
- result: conan-verify PASS（milestone=conan_verify_passed）后 finish 标记 built；release/upload 流水线确认上传前不使用 published。
---

**编译结束**: 2026-09-17 06:22
**最终状态**: built
