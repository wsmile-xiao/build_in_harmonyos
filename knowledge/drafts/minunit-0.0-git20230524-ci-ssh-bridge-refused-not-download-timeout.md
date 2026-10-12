# CI 失败摘要行"源码下载超时"的误诊判别：SSH bridge 拒连 ≠ 下载超时

> Draft: `DRAFT-MINUNIT-GIT20230524-CI-SSH-BRIDGE-REFUSED-NOT-DOWNLOAD-TIMEOUT`
> Stem: `minunit-0.0-git20230524-ci-ssh-bridge-refused-not-download-timeout` — 与同 stem 的 `.kv` 配对

## 基本信息

- **ID**: DRAFT-MINUNIT-GIT20230524-CI-SSH-BRIDGE-REFUSED-NOT-DOWNLOAD-TIMEOUT
- **严重度**: 2
- **类别**: ci|environment|infrastructure|network
- **触发工具**: ci|buildbot
- **阶段**: ci|checkout

## 错误特征

CI 机器人评论的摘要段写着：

```
### 失败诊断
**类别**: 网络问题
**问题**: 源码下载超时
**原因**: Worker 网络受限，无法访问外部源码仓库。已知可达: zlib.net; 已知不可达: ftp.gnu.org。
### 修复指导
1. 确认源码 URL 在 Worker 上可访问
2. 如不可达, 考虑将源码预缓存到 conan 的 s/ 目录
3. 或使用 GitCode/GitHub 镜像作为替代下载地址
```

但展开"失败步骤完整日志"，真相是：

```
--- worker-prep ---
eSSH bridge exec failed: connect failed: connection lost before ready:
  Connection was refused by other side: 111: Connection refused.
hprogram finished with exit code -1
helapsedTime=0.006413          ← 毫秒级！
--- git-clone ---
hgit -c 'safe.directory=*' --version    ← 连这个都失败
eSSH bridge exec failed: ... 111
helapsedTime=0.005539
--- cleanup ---
eSSH bridge exec failed: ... 111
helapsedTime=0.001500
```

**构建从未开始**——三步（worker-prep / git-clone / cleanup）全部在毫秒级被
Worker 的 SSH 桥接服务拒连（connection refused 111），连 `git --version`
这种不涉及网络的命令都执行不了。源码 URL 完全无辜。

## 四条判别特征（同时成立即可定性）

| # | 特征 | 实测值 |
|---|------|--------|
| ① | 失败步骤 worker-prep + git-clone + cleanup 三步全 ❌ | 真实构建（conan create）从未启动 |
| ② | 各步骤 elapsedTime 毫秒级 | 0.001–0.007s（真实下载超时至少秒级） |
| ③ | 日志含 `SSH bridge exec failed: ... Connection was refused by other side: 111` | 每步一条 |
| ④ | 连 `git --version` 都失败 | 0.006s 内 exit -1 |

## 根因分析

CI 机器人的失败评论摘要行按报错类别**粗分类**（"网络问题/源码下载超时"），
其修复指导（预缓存源码 / 使用镜像）针对"下载源 URL 不可达"的情形。但
Worker 侧 SSH 桥接服务未就绪/拒连是另一类故障，被归入同一个"网络问题"
摘要下。适配者若按摘要行的修复指导行事——改 conandata.yml 加镜像
前缀/多源列表——就把一个平台侧故障固化成了 **R39 违规**（官方单 URL
纪律：CI 自动为 GitHub URL 加镜像 fallback，手写镜像 = 绕过统一镜像治理）。

实测数据（minunit PR !14375，2026-10-03 00:48–02:53 故障窗口）：

- 同一 PR 连续 5 轮同签名失败：#68024/#68070/#68096/#68117/#68169
  （CI-002 ×3、CI-034 ×2），**配方零改动**；
- 第 6 轮调度到健康 Worker（CI-019，#68181）→ **CI 绿**；
- 旁证：他队 PR !13398 同款签名多轮失败后亦在健康机（CI-033/CI-023）通过
  ——集群故障是**间歇性**的，重试是唯一正确动作。

## 推荐方案

**方法**: `read-full-log-then-bare-rebuild`

1. **先全文读"失败步骤完整日志"原文**（诊断三铁律之一：摘要行很泛不能定性）。
2. 命中四判别特征 → 定性为 Worker 基础设施故障，配方无问题。
3. 处置 = 评论**裸命令 `/rebuild`** 重试（不带任何补充说明文字），可多次——
   实测第 6 轮在健康 Worker 通过。同类"网络故障重试上限 3 轮"纪律适用于
   真实下载失败；基础设施拒连可按"集群恢复证据"（CI 看板其他 PR 近期
   passed）加试。
4. **禁止动作**：改 conandata.yml 加镜像/多源（R39 违规）、预缓存 s/ 目录、
   回退配方——源码 URL 未被证伪前一律不动配方。
5. 重试仍持续失败超 30 分钟跨 3 轮以上 → 查 CI 看板
   （`GET https://ohpcd.atomgit.com/api/ci/builds?limit=N`）确认故障窗口 →
   平台侧报障（Worker 摘除维修），不是适配层能修的。

## 降级方案

若重试 3 轮以上且跨 30 分钟仍同签名失败：看板确认故障集中 → 平台侧报障，
子任务按外部阻塞回告主 agent，**不带病改配方**。

## 验证命令

```bash
# 判别（对失败评论里的完整日志段）：
grep -c "SSH bridge exec failed" <ci-log>          # 期望 3（三步各一次）
grep -o "elapsedTime=0\.00[0-9]*" <ci-log>          # 全部毫秒级
# 处置：PR 评论区裸命令重试
/rebuild
```

## 取证记录

- 包: minunit 0.0-git20230524（PR !14375）
- 五轮反证样本: #68024/#68070/#68096/#68117/#68169（同签名拒连，配方零改动）
- 第 6 轮绿: #68181（CI-019）
- 旁证: PR !13398 评论流（他队，同款签名多轮后 CI-033/CI-023 通过）
