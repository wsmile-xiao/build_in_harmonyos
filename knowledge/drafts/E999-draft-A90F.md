# E999 — 上游官方站死亡的 R39 权威镜像源认定（prover9 实证）

## 错误特征
```
ERROR: Unable to download prover9-2017-11A source
  URL: https://www.cs.unm.edu/~mccune/prover9/...
  Failed to connect / Connection timed out
```
官方 URL 永久不可达（非网络抖动：多日多次超时）。

## 触发条件
- 构建系统: 任意（本例 conan 手搓 Makefile）
- 阶段: conan create 的 source 下载（conandata.yml URL 失效）
- 实证软件: prover9 2017-11A — 原作者 William McCune（Argonne 国家实验室，Otter/Prover9 作者）
  2023 年去世，官方站 cs.unm.edu/~mccune/ 随之失联

## 根因分析
学术软件常挂靠作者个人/院系页面，作者去世或退休后页面失联是常态。R39 要求源可追溯、
不可随意换成匿名 fork——镜像源必须论证"承继权威性"，否则供应链不可审计。

## 解决方案

### 推荐方案（四步论证链，prover9 实证）
1. **死亡证据**：官方站实测不可达（curl 超时记录）+ 作者去世/项目终止的公开事实；
2. **承继关系**：考察候选镜像仓的维护主体与谱系——ai4reason/Prover9 承载末代官方维护人
   Bob Veroff 的延续线（LADR-2017-11A 即其维护的末版），社区维护（⭐63，GPL-2.0），
   非个人随意 fork；
3. **不可变锚点**：不用分支/HEAD，锁定 40 位 commit 的 codeload archive URL
   `https://github.com/ai4reason/Prover9/archive/cdca95a51d3c3459b8fd2ebbb5ac1504be2172e3.tar.gz`
   并记录 sha256=3a2f7a15367a8a438db0a08349a42204b5a4f08002bd84c29fd202eba1a56f04；
4. **留痕复核**：论证链写入 notes.md 与 PR body"补充说明"段，供人审复核。

### 禁止做法
- ❌ 直接用 GitHub 分支头 URL（HEAD 漂移，不可复现）
- ❌ 用无法说明谱系的个人 fork（供应链不可审计，违反 R39）
- ❌ 用 README 里随手贴的第三方网盘/短链

## 验证
```bash
curl -sI --max-time 10 https://www.cs.unm.edu/~mccune/prover9/ | head -1   # 超时
curl -sL -o p9.tar.gz https://github.com/ai4reason/Prover9/archive/cdca95a51d3c3459b8fd2ebbb5ac1504be2172e3.tar.gz
sha256sum p9.tar.gz   # = 3a2f7a15…a56f04
```

## 关联条目
- 相关: E477/E017（下载层网络故障族，本条是"源权威性"维度而非连通性维度）
