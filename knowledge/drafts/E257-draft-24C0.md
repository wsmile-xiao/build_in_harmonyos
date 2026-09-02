# E257 — clean-verify G0 对无 configure 的 Makefile 项目硬失败属预期（框架 autotools 假设）

## 错误特征
`ohc-run.py clean-verify <软件> <版本>` 的 G0 阶段报告 configure 失败，退出码 127；日志形如：
`G0.*configure.*failed.*exit 127` 或 `./configure: No such file or directory`。

## 触发条件
- 构建系统: 纯 Makefile（无 configure 脚本），如 NetSurf NSSHARED 系（libwapcaplet、libnsutils、libnslog、libdom 等）
- 阶段: configure（clean-verify 第 3/10 步）

## 根因分析
clean_verify.py 的 G0 阶段硬编码先执行 `./configure`（autotools 框架假设）。纯 Makefile 项目没有 configure 脚本，在该阶段必然 exit 127。这是框架层 G0 的构建系统假设局限，不是配方缺陷；且 clean-verify 属非阻塞门禁（finish 第 3/10 步），权威的干净构建可复现验证是 conan-verify G2 的 conan create（从干净源码 build+test）。

## 解决方案

### 推荐方案
在 notes.md 中记录 clean-verify G0 configure 失败为预期（本配方 libwapcaplet 0.4.3.2 已记录），不修改配方伪造 configure；以 conan-verify G2 真实 conan create 作为干净构建验证。

### 禁止做法
- ❌ 手动编写 configure 脚本（E058 明令禁止手动编写 autoconf 生成物；Makefile 项目本身不需要，会破坏构建系统正确性，导致本地/CI 行为不一致）

## 验证
```bash
python3 scripts/ohc-run.py conan-verify <软件> <版本>
# G2 conan create 从干净源码 build+test 通过即视为干净构建可复现
```

## 关联条目
- 相关: E058, E168
