# E322 — CI git-clone 步骤失败：Worker 的 git 二进制缺 libz.so

> **结构化数据**: [E322-draft-2FFB.kv](E322-draft-2FFB.kv) (draft) | **原则**: 无
> **严重度**: 🔴 blocking | **分类**: environment, toolchain, ohos

---

## 错误特征

```
--- git-clone ---
git -c 'safe.directory=*' --version
Error loading shared library libz.so: (needed by /data/service/hnp/bin/git)
program finished with exit code 127
```

## 触发条件

- 工具: `/data/service/hnp/bin/git`（buildbot worker 的 git 2.45.2）
- 阶段: CI 流水线 git-clone 步骤（发生在 checkout-pr / conan 配方可见之前）
- 平台: HarmonyOS OHOS worker 集群

## 根因分析

worker 上 `/data/service/hnp/bin/git` 的 NEEDED 依赖包含 `libz.so`，
但其 RUNPATH 硬编码为构建机路径 `/code/deps_install/lib`（worker 上不存在），
且 musl ldso 不支持 `$ORIGIN` 扩展（见 E019），只能依赖系统默认加载路径。

- **健康 Worker**（CI-002/CI-012/CI-036）：`/usr/lib/libz.so.1` 存在 → git 正常
- **故障 Worker**（CI-005/CI-009/CI-020）：`/usr/lib/libz.so.1` 缺失 → git 启动失败 exit 127

该失败发生在 git-clone 步骤，**配方代码（conanfile.py 等）尚未可见**，
配方侧无法干预——这是纯粹的 Worker 环境问题，PR 代码本身无缺陷。

## 解决方案

### 推荐方案（Worker 侧，CI 维护者执行）
在故障 Worker 上安装 zlib（libz.so.1）到系统默认库路径 `/usr/lib`，
使 git 可加载：

```bash
# 验证当前状态
/data/service/hnp/bin/git --version
ls -la /usr/lib/libz.so.1

# 修复：安装 libz.so.1 到 /usr/lib 后重试
/data/service/hnp/bin/git --version   # 应输出 git version 2.45.2
```

### 回退方案（E186 先例，patchelf 修 RUNPATH）
复制 git 到可写目录，用 patchelf 把 `/usr/lib` 加入 RUNPATH，再签名：

```bash
cp /data/service/hnp/git.org/git_2.45.2/bin/git ~/tmp/git-local
patchelf --set-rpath '/usr/lib:/code/deps_install/lib' ~/tmp/git-local
binary-sign-tool sign ~/tmp/git-local   # ELF 修改后必须重签（E077）
```

### 禁止做法
- ❌ 当作 PR 配方问题反复 `/rebuild`——git-clone 在配方可见之前，重试只会命中故障 Worker
- ❌ 在配方/仓库内尝试修改 `/data/service/hnp/bin/git` 或 `/usr/lib`——配方无法触达系统层

## 验证

```bash
/data/service/hnp/bin/git --version
# 应输出: git version 2.45.2（不再报 libz.so 错误）
```

## 关联条目

- 相关: E186（cargo 缺 libz.so，musl ldso RUNPATH 同源问题）
- 相关: E019（musl 不支持 $ORIGIN RPATH 扩展）
