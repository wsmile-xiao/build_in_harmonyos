# dawg 1.2 外部引证原始留档（可离线复核）

本目录保存 `notes.md`「上游测试基准过期」一节所引用的证据，使审阅者无需联网、也无需信任
叙述即可自行核对。**除 `rng-old-semantics.diff`（本 PR 自带的实验用还原 diff，非抓取所得，
见下节末尾）之外**，其余文件均为 2026-09-11 从下述 URL 直接抓取的原样内容
（未做任何加工、未删除 HTML 标签），每份附抓取时的 HTTP 状态码与 sha256。

## 外部抓取的原样字节

| 文件 | 来源 URL | HTTP | 字节 | sha256（前 16） |
|------|---------|------|------|----------------|
| `debian-1.2-5-rules.txt` | https://sources.debian.org/data/main/d/dawg/1.2-5/debian/rules | 200 | 842 | `41ad40447d5e735e` |
| `debian-1.2-5-changelog.txt` | https://sources.debian.org/data/main/d/dawg/1.2-5/debian/changelog | 200 | 1771 | `6867561ed133761f` |
| `debian-sources-api-versions.json` | https://sources.debian.org/api/src/dawg/ | 200 | 394 | `941dd4805572bd91` |
| `debian-med-2018-07-msg00017.html` | https://lists.debian.org/debian-med/2018/07/msg00017.html | 200 | 6330 | `d2cffa090c668b3b` |
| `debian-bug-903886-2018-07.html` | https://alioth-lists.debian.net/pipermail/debian-med-packaging/2018-July/063988.html | 200 | 4430 | `dc5af80f14140706` |
| `debian-bug-903886-2020-10-author-reply.html` | https://alioth-lists.debian.net/pipermail/debian-med-packaging/2020-October/085093.html | 200 | 4474 | `4ecf891da8c9520e` |
| `github-issues-56-from-device.html` | https://github.com/reedacartwright/dawg/issues/56 | **404** | **9** | `0019dfc4b32d63c1` |

## 本 PR 自带的实验用文件（非外部抓取）

| 文件 | 来源 | 字节 | sha256（前 16） |
|------|------|------|----------------|
| `rng-old-semantics.diff` | 作者构造，用于 `notes.md`「第二步：旧语义还原实验」 | 511 | `75941be4b027fff6` |

该文件**不是**从任何 URL 抓取的原始字节，而是把 `src/rand.h` 的 `rand_real()`/`rand_bool()`
还原为 v1.0.0 语义的还原改动（1 个 hunk；union 位拼接 + `<=`），用途是让 LCP 表可在仓库内复算。

完整 sha256 复算（**注意 `sha256sum *` 会一并列出 `README.md` 自身，故输出行数比表格多 1**）：

```sh
cd archives/d/dawg/1.2/reports/evidence
sha256sum ./*.txt ./*.html ./*.json ./*.diff    # 8 份证据文件
sha256sum *                                     # 另含 README.md 自身

```

## 每份证据证明什么（逐条可自行核对）

### 1. `debian-1.2-5-rules.txt` —— 发行版显式忽略该失败测试，且**其注释本身就给出了上游 issue 编号**

第 24-30 行原文（可 `grep -n -A6 override_dh_auto_test` 复核）：

```make
override_dh_auto_test:
ifeq (,$(filter nocheck,$(DEB_BUILD_OPTIONS)))
	# FIXME: This test fails - but let the build pass anyway for the moment
	#  see https://github.com/reedacartwright/dawg/issues/56
	cd tests && PATH=$$PATH:$(BINDIR) sh test0.sh || true
endif
```

这一点很关键：上游 issue 编号 `#56` **并非只来自 GitHub 页面**（本设备访问该 issue 路径返回 404，
见第 7 行证据），而是由 Debian 官方源码包内的 `debian/rules` 注释独立书写并随发行版发布。
换言之，该编号有**第二条可离线复核的来源**。

### 2. `debian-1.2-5-changelog.txt` —— 该测试失败被作为发行版已知问题记录在案

`grep -n -i "test" debian-1.2-5-changelog.txt` 可见 1.2-4 条目里的
`Document issues with test (see upstream issue #56)`，与上一条互相印证（时间线与版本号一致）。

### 3. `debian-source-api-versions.json` —— 版本与套件归属（用于交叉核对上述文件的版本上下文）

内容为 `{"package":"dawg", ..., "versions":[{"version":"1.2-5","suites":["forky","sid"]}, ...]}`，
即 `debian/rules` 取自当前 sid/forky 的 1.2-5。

### 4/5/6. 邮件列表归档 —— **amd64/glibc/GCC 上的实际 diff 输出**与**上游作者本人的答复**

- `debian-med-2018-07-msg00017.html`（Debian Med 列表，2018-07-05，Andreas Tille）：
  正文贴出了在 Debian amd64 构建时 `test0.sh` 的实际 diff。可自行核对其中出现
  `TCCTTGACCAGTTAGCAAGACGATATGCATCAAGTGCACTGGC`（即程序实际输出侧）与
  `AGGAACTGGTCACGTTCTGCTATACGTAGTTCACGTGACCGCATTCAGAAAAATGCGACT`（签入基准侧）：

  ```sh
  grep -c 'TCCTTGACCAGTTAGCAAGACGATATGCATCAAGTGCACTGGC' debian-med-2018-07-msg00017.html   # ≥1
  ```

  这直接支撑 `notes.md` 的论断：**非 OHOS 平台（amd64 + glibc + GCC）上，未修改源码同样产出
  这份被签入基准拒绝的输出**。
- `debian-bug-903886-2018-07.html`：Debian bug #903886「dawg: Test suite fails」原文，
  说明该失败在启用测试后立即暴露、且明确标注 `Tags: upstream`。
- `debian-bug-903886-2020-10-author-reply.html`：转发上游作者的 GitHub 通知邮件，标题
  `Re: [reedacartwright/dawg] Test script fails (#56)`，正文原文：

  > I don't believe that anyone has ever ported the test script to the 2.0 code base.
  > 2.0 is still technically in development which is why I haven't tagged any releases.

  这支撑「上游未把该测试迁移到新代码库/构建系统」的判断，并**再次独立出现 `(#56)` 编号**。

### 7. `github-issues-56-from-device.html` —— 如实记录本次抓取失败

内容就是 `Not Found`（9 字节）。本设备访问
`https://github.com/reedacartwright/dawg/issues/56` 返回 **HTTP 404**（同一设备上
`https://github.com/` 本身返回 **200**，即失败的是该具体路径、不是主机整体；
9 字节的 `Not Found` 也不是 GitHub 常规 404 页面形态，疑与设备侧出口网关有关），
因此**本任务没有直接读到该 issue 页面本身**。本目录的作用正是把这个事实也留档，
而不是让读者以为作者读到了原文——issue 编号的采信依据是上面第 1、6 条
（Debian 官方包文件 + 邮件列表归档），不是这次失败的抓取。

## 与 `notes.md` 的对应关系

`notes.md` 的每一条跨平台论断都对应到本目录的具体文件。本目录中**由作者产出**的仅
`rng-old-semantics.diff`（实验用还原 diff，其内容可按上文命令逐字节复算），其余文件均为
外部原始字节。审阅者若认为上述任何一条证据不足以支撑相应论断，可按文件逐一反驳。
