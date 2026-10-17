# E999 — conan 版本号大写字母 → must be all lowercase（prover9 实证）

## 错误特征
```
ERROR: Conan packages names 'prover9/2017-11A@ohpcd/stable' must be all lowercase
```
（conan create 阶段硬失败；本地 conan-verify G2 直接 FAIL。CI 侧同规则为 L0m-5 slug 校验 +
L0n 分支名精确匹配。）

## 触发条件
- 构建系统: conan（任意配方）
- 阶段: conan create / conan-verify G2 / CI L0m-5、L0n
- 实证软件: prover9 上游官方发布名 **2017-11A (CIIRC)**（LADR-2017-11A）

## 根因分析
conan 引用（name/version）字符集强制 `[a-z0-9][a-z0-9._+-]*` 全小写；上游版本字符串的
大写字母（A273、2017-11A、1.2b 类）直接踩雷。CI 同规则三连：L0m-5 拦版本目录、L0n 拦分支名
（大小写敏感、精确等于 包名-版本slug）、平台按分支名+作者关联任务。

**附带坑**：本机 HMDFS 大小写不敏感——`mv 2017-11A 2017-11a` 报 `Invalid argument`、
`git branch -m old-A new-a` 报 `branch already exists`（同名冲突判定）。须两步中转改名。

## 解决方案

### 推荐方案（三处统一小写化）
1. 版本目录：`archives/p/prover9/2017-11a/`
2. conanfile.py：`version = "2017-11a"`（注释注明上游口径 2017-11A）
3. 分支：`feat/prover9-2017-11a`（L0n 精确匹配）
4. commands.json / manifest.yaml / test_package/MANIFEST.yml 同步小写 slug

HMDFS 两步中转：
```bash
mv archives/p/prover9/2017-11A archives/p/prover9/p9-tmp
mv archives/p/prover9/p9-tmp archives/p/prover9/2017-11a
git branch -m feat/prover9-2017-11A p9-tmp-branch
git branch -m p9-tmp-branch feat/prover9-2017-11a
```

注意：二进制 `--version` 横幅输出 `2017-11A (CIIRC)` 是上游行为，测试断言仍应匹配
**大写原串**（横幅断言与 conan slug 是两个层面）。

### 禁止做法
- ❌ 推含大写版本段的分支（挂 L0n/R40 + 平台任务关联失败）
- ❌ 只改 conanfile 不改目录/分支（L0m 一致性校验失败）

## 验证
```bash
conan create archives/p/prover9/2017-11a ...   # 不再报 lowercase
git branch --show-current                        # feat/prover9-2017-11a
prover9 --version | grep -c "2017-11A"          # 1（横幅仍大写，断言用原串）
```

## 关联条目
- 相关: 先例 mawk A273 类版本在 CI 注释中同被引用为反例（must be all lowercase）
