# DRAFT — 上游测试脚本依赖宿主机专有外部二进制，断言应复算而非跳过

> Status: **Draft**（待主编 promote） | severity: `2` | category: `testing` | Updated: 2026-10-02
> 源文件：`knowledge/drafts/DRAFT-mashmap-3.1.3-upstream-test-external-bedtools-unrunnable.kv`
> 来源：mashmap 3.1.3 适配（`feat/mashmap-3.1.3`）

---

**关键词**：bedtools, samtools, scripts/test.sh, 上游测试, 宿主机专用二进制, 覆盖度复算, 阈值断言, CI 能力矩阵

## 现象（error_signature）

```text
scripts/test.sh: line 6: bedtools: command not found
scripts/test.sh: line 10: bedtools: Cannot exec
```

上游 CI 的第三个步骤 `scripts/test.sh <fai> <paf> 0.92` 在 CI clean 环境里逐字不可执行。

## 根因（root_cause）

mashmap 3.1.3 的测试不是自包含的。`.github/workflows/build-and-test.yml` 的三个步骤：

```yaml
- name: Basic version test
  run: build/bin/mashmap -v
- name: Align yeast genomes
  run: build/bin/mashmap -r data/scerevisiae8.fa.gz -q data/scerevisiae8.fa.gz \
        --pi 95 -n 1 -Y '#' -o scerevisiae8.paf
- name: Test yeast coverage
  run: scripts/test.sh data/scerevisiae8.fa.gz.fai scerevisiae8.paf 0.92
```

第三步的脚本内部：

```bash
bedtools sort | bedtools merge > $PAF.query+target.bed
bedtools intersect -a $PAF.sequences.bed -b $PAF.query+target.bed -wo > $PAF.overlap.bed
awk '... coverage[$1] / len[$1] ...' > $PAF.coverage.txt
awk -v threshold=$COVERAGE 'NR > 1 && $2 < threshold { flag = 1 } END { if (flag) exit 1 }'
```

`bedtools` 是 x86_64 Linux 专用发行版二进制：

- 不在 OpenHarmony SDK/NDK 工具链内；
- 没有跨平台构建脚本，做成 conan 包不成立；
- CI worker 上无包管理器、无 root。

按 W0b 的口径核验——**「历史/上游命令在 CI 环境里逐字可执行吗」**——答案是不可执行。

但关键在于：脚本承载的是**可复算的断言**，不是不可复现的黑盒。bedtools 在这里做的两件事
（区间并集、区间求交）都能在配方语言里直接算。于是正确解法不是跳过，而是**复算**。

## 推荐方案（rec_approach）

三步：

1. **逐字核验 + 写清具体技术原因**（哪个工具、为什么拿不到、为什么不能交叉构建）。
   「没环境」不是理由。
2. **保留断言、复算算术**。把 PAF 的 query 区间按序列名分组求并集长度，除以 `.fai` 里的
   序列长度，与脚本传入的**同一阈值**比较。**不改上游脚本、不放宽阈值**。
   实测口径：136 条 contig 全部被覆盖，最低覆盖度 `0.9419 ≥ 0.92`。
3. **如实声明**。`test_package/MANIFEST.yml` 的该条 `upstream_tests` 写明
   「等价复算，未直接执行脚本」及原因；PR 正文按 R51 回填实测 N/N′ 与通过率。

## 备选方案（fallback）

若断言**不可复算**（依赖外部参考数据库、不可获得的黄金数据等），就老实标成「未执行」，
在 `MANIFEST.yml` 里写明原因，并用消费者用例补上等价的功能覆盖。
绝不能删用例假装通过，也绝不能改上游脚本让它「看起来通过」。

## 禁忌（forbid）

```python
self.run("bedtools intersect ...")          # ❌ 配方/用例里调用外部宿主工具
apt install bedtools                       # ❌ CI worker 无 root、无包管理器
self.output.info("upstream test skipped")  # ❌ 以跳过冒充执行
```

后果：`conan create` 在 `test()` 阶段以 `command not found` 失败；或更糟——
断言被静默跳过时 `conan create` 仍返回 0，L1 系列门禁也看不出问题，
PR 声称的上游测试通过率与事实不符，触发「门禁未绿却报 success」红线。

## 影响面（affected_scope）

所有「上游测试脚本依赖未随包分发的宿主工具」的适配项目：

- 生信：`bedtools` / `samtools` / `bgzip`
- 音视频：`ffmpeg` / `sox`
- GIS：`ogr2ogr`
- 文档：`pdflatex` / `pandoc`

红灯文案往往只说「命令找不到」，看不出是上游脚本自身的宿主依赖问题，
容易被反复盲推浪费 CI 额度（R42 修复轮聚焦的反面教材）。

## 关联

- `principles:` P001, P003
