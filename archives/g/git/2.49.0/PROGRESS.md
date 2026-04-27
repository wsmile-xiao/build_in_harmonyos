# git 2.49.0 — 编译进度

> 档案创建时间: 2026-04-25 00:00:00
> 最后更新: 2026-04-25 (当前状态)
> 当前会话 ID: (可选，用于多轮对话追踪)

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | git |
| 版本 | 2.49.0 |
| 状态 | 🔵 进行中 / ✅ success / ⚠️ partial / ❌ failed |
| 构建系统 | autotools/cmake/meson/... |
| 源码路径 | URL |

## 二、编译阶段（checkbox 实时更新）

### Phase 1: 环境准备
- [ ] ohc-run.py init-build 完成 / 源码下载解压

### Phase 2: 编译（configure + make + make install）
- [ ] configure 完成（记录参数和耗时）
- [ ] make 编译完成（记录错误和修复）
- [ ] make install 完成

### Phase 2.5: 独立目录安装验证（⭐ 必须做）
- [ ] 干净源码 + 补丁应用
- [ ] 独立 TEST_PREFIX configure + make install
- [ ] 功能回归测试结果

### Phase 3: 测试验证
- [ ] make check / make test 结果
- [ ] 安全弹窗触发确认

### Phase 4: 预编译包制作（⭐ verify PASS 后必须）
- [ ] Step 1-10 打包流程（见 packaging.md）

### Phase 5: 归档收尾
- [ ] 补丁生成（ohc-run.py refresh-patch --auto）
- [ ] manifest.yaml / README.md / PROGRESS.md 更新
- [ ] ohc-run.py verify-build 质量门禁

## 三、对话记录（⭐ 断点续传核心）

> **每轮对话结束时必须更新此节。新 AI 会从这里恢复上下文。**

### 对话 #N — 2026-04-25 HH:MM
**操作**: （做了什么，如"执行 configure"、"修复 xxx bug"、"制作预编译包"）
**结果**: （成功/失败/部分成功，附关键输出摘要）
**发现的问题**: （遇到的坑、错误信息、根因分析）
**当前状态**: （精确到哪个步骤，下一步该做什么）
**遗留问题**: （未解决的、需要下轮继续的）

---

### 对话 #1 — 2026-04-25 00:00
**操作**: 执行 ./configure --prefix=$DEFAULT_PREFIX
**结果**: （待填写）
**发现的问题**: （待填写）
**当前状态**: Phase 2 configure 进行中
**遗留问题**: 无

（后续每轮对话追加...）

## 四、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| ... | ... | ... | ... |

## 五、预编译包交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| ... | ... | ... |

## 六、结束记录
- **最终状态**: ...
- **结束时间**: ...
---

**编译结束**: 2026-04-25 20:38
**最终状态**: partial

## 七、发现的问题及解决方案（2026-04-27 补充）

### 问题 1：templates 目录缺失

**症状**：
```
warning: templates not found in /storage/Users/currentUser/usr/local/share/git-core/templates
```

**根因**：
- git 源码中有 templates 目录（包含 hooks/*.sample、info、description）
- 打包时只复制了空目录，没有复制 templates 内容
- 原因：使用 DESTDIR 模式时 templates 没有被正确复制

**解决方案**：
- 从系统预装 git 复制 templates 内容
- 打包时包含完整的 share/git-core/templates/ 目录

### 问题 2：safe.directory 权限检查

**症状**：
```
fatal: detected dubious ownership in repository at '/storage/Users/currentUser/Runner004/cmd-pkgs'
```

**根因**：
- git 2.35+ 引入的安全特性
- HMDFS 文件系统有特殊的 UID 映射
- 仓库目录的 owner 和当前用户不一致时拒绝执行

**解决方案**：
- 创建系统级 gitconfig 配置 `safe.directory = *`
- 在预编译包中包含 etc/gitconfig 文件
- 安装脚本自动复制到 ~/usr/local/etc/gitconfig

## 八、修订后的预编译包结构

```
git-2.49.0-ohos-aarch64.tar.gz
├── bin/git                    # git 二进制
├── share/git-core/templates/  # 完整 templates
│   ├── hooks/*.sample         # git hooks 示例
│   ├── info/exclude           # exclude 文件
│   └── description            # 描述文件
├── etc/gitconfig              # 系统级配置 (safe.directory=*)
└── install-git-2.49.0.sh      # 安装脚本
```

---

**修订日期**: 2026-04-27
**修订内容**: 补充 templates 和 safe.directory 问题的解决方案
