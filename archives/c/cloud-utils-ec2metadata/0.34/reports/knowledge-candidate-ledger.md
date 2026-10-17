# 知识候选台账 — cloud-utils-ec2metadata 0.34（第一轮适配）

> 本台账按 SKILL 知识治理要求记录：每项非噪声候选的真实错误、根因、修复、验证、
> 适用范围、四范围查重结果与七轴查重结论，最后给出路径决定。
> 适配库：cloud-utils-ec2metadata 0.34（上游 canonical/cloud-utils tag 0.34）。

## 一、候选清单

### C1. Makefile install(1) 长选项 `--mode=0644` 不被 HarmonyOS 支持
- **真实错误**：`make install` 阶段 `install(1)` 报错（HarmonyOS 的 install 不支持 `--mode=` 长选项）。
- **根因**：上游 Makefile 使用 GNU coreutils 风格的 `install --mode=0644`；HarmonyOS 平台 install 仅支持短选项 `-m`。
- **修复**：`patches/0001-Makefile.patch` — `install $(manpages) "$(MANDIR)/" --mode=0644` → `-m 0644`。
- **验证**：W3 本地 CI（build_and_test.sh）通过：L0/L1/L2/L4/L5 全 pass，`conan create` 成功安装 7 个 bin 脚本与 4 个 man 页；`.ci-result.json` exit_code=0。
- **适用范围**：所有用 GNU `install --mode=` 语法的 Makefile 类脚本包（跨库可复用）。
- **四范围查重**：
  - graph/index.tsv：未直接命中 `--mode=0644`；相近 E087（`install -c -m 755` 替代 cp）、E174（`install -m` → cp 兜底）。
  - knowledge/doc/：无 `--mode` 专项条目。
  - graph/*.kv：E087.kv/E174.kv 覆盖「install 参数兼容」方向。
  - knowledge/drafts/：无相同条目。
- **七轴查重**：exact_duplicate=false；causal_duplicate=false（与 E087 同为 install 兼容但触发点不同：长选项 vs 分离参数）；trigger_overlap=部分（安装阶段兼容性）；solution_overlap=部分（改 install 参数形式）；combination_novelty=false；boundary_novelty=false；test_migration_novelty=false。
- **结论**：与既有知识（E087/E174 + 0.33 归档同款修复）同质，**复用既有知识，不新建草稿**。

### C2. 脚本 shebang 硬编码 `/bin/bash`、`/usr/bin/python3`，HarmonyOS 无这些路径
- **真实错误**：直接执行脚本报 "bad interpreter" / "No such file or directory"。
- **根因**：HarmonyOS 无 `/bin/bash`、`/usr/bin/python3`；上游脚本 shebang 硬编码。
- **修复**：`patches/0002-0006` — 5 个脚本 shebang 改 `#!/usr/bin/env bash` / `#!/usr/bin/env python3`。
- **验证**：W3 L2 smoke 测试：cloud-localds/growpart/mount-image-callback/resize-part-image/vcs-run/write-mime-multipart `--help` 全 OK；ec2metadata `--help` 输出正常（上游 usage() exit 1 为设计行为）。
- **适用范围**：所有 shebang 硬编码解释器绝对路径的脚本工具（跨库通用）。
- **四范围查重**：
  - graph/index.tsv：**命中** E037（env shebang）、E049（硬编码解释器路径）、E165（/bin/bash、OHOS）、E143（python3 shebang）。
  - knowledge/doc/：E037.md/E049.md/E165.md 已覆盖。
  - knowledge/drafts/：DRAFT-E363（bash+TMPDIR）、DRAFT-E327 等相近但非本主题。
- **七轴查重**：exact_duplicate=是（E037/E165 已完整覆盖 env shebang 修复）；其余轴无新增。
- **结论**：**完整复用既有知识（E037/E049/E165/E143），不新建草稿**。

### C3. ec2metadata IMDSv2 token 端点硬编码 169.254.169.254，离线环境功能测试挂起
- **真实错误**：mock 直连测试中子进程对 169.254.169.254 的 connect 成 SYN 黑洞，用例挂起（>120s 超时）；直接绑 169.254.169.254 或 iptables 重定向在本机无 root/无 ip/无 iptables 不可行。
- **根因**：`session_token_url` 为全局常量 `http://169.254.169.254/latest/api/token`（不受 `-u` 覆盖）；`_test_connectivity` 直连探测；无外网时黑洞路由慢超时。另发现上游 `usage()` 对 `--help` 也 exit 1 且写 stderr。
- **修复（测试方法）**：本地 socketserver 同时扮演正向代理 + IMDS mock，子进程注入 `http_proxy/https_proxy`（no_proxy 置空），token PUT 与 meta-data GET 全部经代理到达本地 mock，按绝对 URL 拆路径应答；元数据基址用 mock 真实端口（满足直连探测）。同时按输出文本断言 `--help` 而非 rc。
- **验证**：`EC2METADATA_BIN=... python3 test_ohos_ec2metadata.py` → `OHOS TEST PASSED`（rc=0）；instance-id/ami-id 真实返回 mock 值；该测试已随 test_package 被 conan create 与 W3 消费。
- **适用范围**：所有硬编码知名外部服务端点（EC2/云厂商 metadata 169.254.169.254 等）的 Python/shell CLI 工具在离线环境做功能验证；同型：ec2metadata、cloud-init、instance-id/region 查询脚本。
- **四范围查重**：
  - graph/index.tsv：**零命中**（grep 169.254/IMDS/ec2metadata/mock proxy 无结果）。
  - knowledge/doc/：零命中。
  - graph/*.kv：零命中。
  - knowledge/drafts/：仅 DRAFT-libasd 提到 "hermetic" 一词，与本候选（测试方法）无关；DRAFT-E363 是 runner 假绿防护，方向不同。
  - archives/c/cloud-utils/0.33：0.33 归档只做 shebang/install 修复，**无**功能测试方法条目。
- **七轴查重**（详下）。

## 二、C3 七轴查重明细

| 轴 | 判定 | 说明 |
|----|------|------|
| exact_duplicate | false | 四范围均无同条目 |
| causal_duplicate | false | 无既有条目由同一根因（IMDS token 硬编码 + 离线黑洞）产生 |
| trigger_overlap | 部分 | 触发面与 E201（/bin/bash 等运行时依赖）、E363（测试 runner）同在"脚本工具测试"域，但触发器不同（端点不可达 vs 解释器缺失/假绿） |
| solution_overlap | 部分 | E325/E363 同在 test_package 内做环境适配，但解法（代理 mock 路由）全新 |
| combination_novelty | true | 「硬编码端点脚本工具 + 离线功能验证」组合无既有方案 |
| boundary_novelty | true | 边界清晰：HTTP 功能路径可 mock；内核/设备依赖（growpart 分区用例）不可 mock |
| test_migration_novelty | true | 该方法可迁移至 cloud-init 等一切 169.254.169.254 客户端 |

- **覆盖/新增差异**：既有条目覆盖 shebang/install 修复（本库已复用）；C3 新增"代理 mock 路由法"测试方法论，未覆盖。
- **关系字段**：similar_to=E037,E049,E201,E325,E363；caused_by=无；prerequisite_of=无；conflicts_with=无。
- **适用边界/反例**：仅 TCP/HTTP 路径；raw socket 客户端不受 http_proxy 约束；`--help` 断言须以文本为准（usage() exit 1 是设计行为）。

## 三、路径决定

- **reuse_existing**：C1（install -m）、C2（env shebang）→ 复用 E037/E049/E087/E143/E165/E174 与 0.33 归档知识。
- **new_draft**：C3（IMDS 代理 mock 测试法）→ 已验证（OHOS TEST PASSED，真实命令/退出码）、可跨库复用、查重未命中且存在新增差异 → **路径 B（知识库扩展）成立**。
- 已建立同 stem 草稿对：
  - `knowledge/drafts/DRAFT-cloud-utils-ec2metadata-0.34-imds-mock-proxy-test.kv`
  - `knowledge/drafts/DRAFT-cloud-utils-ec2metadata-0.34-imds-mock-proxy-test.md`
- **path_a_no_knowledge**：不适用（本库存在新增知识）。

## 四、查重执行记录（命令与范围）

- 范围 1 graph/index.tsv：`grep -iE 'shebang|install.*mode|--mode|cloud-utils|ec2metadata|169\.254|imds|bin/bash|usr/bin/python' knowledge/graph/index.tsv`
- 范围 2 knowledge/doc/：`grep -riE '169\.254|IMDS|ec2metadata|mock.*proxy' knowledge/doc/*.md`
- 范围 3 knowledge/graph/*.kv：`grep -riE '169\.254|IMDS|ec2metadata|mock.*proxy|--mode|mode=0644' knowledge/graph/*.kv`
- 范围 4 knowledge/drafts/：`grep -riE '169\.254|IMDS|ec2metadata|mock.*proxy|hermetic|http_proxy' knowledge/drafts/*.kv`
- 归档对照：`archives/c/cloud-utils/0.33/{notes.md,manifest.yaml,conanfile.py,conandata.yml}` 全读。

*生成时间：2026-09-08；执行端 pc1-33；task_id: cloud-utils-ec2metadata-0.34-r01-pc1-33-20260908T012950Z*
