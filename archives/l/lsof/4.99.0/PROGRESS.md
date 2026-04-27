# lsof 4.99.0 — 编译进度

> 档案创建时间: 2026-04-25 21:18
> 最后更新: 2026-04-25 21:30
> 当前会话 ID: lsof-compile-001

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | lsof |
| 版本 | 4.99.0 |
| 状态 | ⚠️ partial (平台限制) |
| 构建系统 | Configure (lsof特有) + make |
| 源码路径 | https://api.github.com/repos/lsof-org/lsof/tarball/4.99.0 |

## 二、编译阶段（checkbox 实时更新）

### Phase 1: 环境准备
- [x] ohc-run.py init-build 完成 / 源码下载解压 (2026-04-25 21:18)
- [x] 修改 Mksrc 的 shebang (#!/bin/bash → #!/data/service/hnp/bin/bash)

### Phase 2: 编译（Configure + make + make install）
- [x] Configure 完成（./Configure -n linux，设置 LINUX_CONF_CC=clang, LSOF_INCLUDE=OHOS sysroot）
  - 参数: `-n linux` (避免 AFS/customization/inventory checks)
  - 生成的 CFGF: `-DLINUXV=00000 -DHASIPv6 -DHASNORPC_H -DNEEDS_NETINET_TCPH -DHASUXSOCKEPT -DHASPTYEPT -DHASSOSTATE -DHASSOOPT -DHAS_DUP2 -D_FILE_OFFSET_BITS=64 -D_LARGEFILE64_SOURCE`
- [x] 修复 dlsof.h 头文件冲突（sockaddr_storage 重复定义）
  - 修改 lib/dialects/linux/dlsof.h
  - 添加 __OHOS__ 条件到 tcp 头文件选择
  - 定义 __kernel_sa_family_t 并设置 _UAPI_LINUX_SOCKET_H 防止重复包含
- [x] make 编译完成 (2026-04-25 21:25，使用 CC=clang)
- [x] make install 完成 (手动安装，lsof Makefile 没有默认 install 规则)

### Phase 2.5: 独立目录安装验证（⭐ 必须做）
- [x] DESTDIR=$TEST_PREFIX staging 安装完成
- [x] 二进制签名尝试失败（binary-sign-tool: is not trust command）
- [ ] 功能回归测试 - **平台限制**: lsof 无法正常执行，/proc 文件系统访问受限

### Phase 3: 测试验证
- [ ] make check / make test 结果 - lsof 无标准测试套件
- [ ] 安全弹窗触发确认 - 未签名二进制可执行，但功能受限

### Phase 4: 预编译包制作（⭐ verify PASS 后必须）
- [ ] Step 1-10 打包流程（见 packaging.md）

### Phase 5: 归档收尾
- [ ] 补丁生成（ohc-run.py refresh-patch --auto）
- [ ] manifest.yaml / README.md / PROGRESS.md 更新
- [ ] ohc-run.py verify-build 质量门禁

## 三、对话记录（⭐ 断点续传核心）

> **每轮对话结束时必须更新此节。新 AI 会从这里恢复上下文。**

### 对话 #1 — 2026-04-25 21:18-21:30
**操作**: 
1. ohc-run.py init-build lsof 4.99.0 (URL: GitHub API)
2. 修改 lib/dialects/linux/Mksrc shebang (#!/bin/bash → #!/data/service/hnp/bin/bash)
3. ./Configure -n linux (设置 LINUX_CONF_CC=clang, LSOF_INCLUDE=OHOS sysroot)
4. 修改 lib/dialects/linux/dlsof.h 解决 sockaddr_storage 重复定义问题
5. make CC=clang 编译成功
6. 手动安装到 staging 和本地

**结果**: 
- ✅ 编译成功，生成 lsof 二进制文件 (297KB, aarch64, dynamic linked to libc.so)
- ⚠️ 运行受限：lsof 无输出，/proc 文件系统访问可能受限（鸿蒙平台限制）

**发现的问题**: 
1. Mksrc shebang 指向 /bin/bash（不存在），需改为 /data/service/hnp/bin/bash
2. Configure 使用 /usr/include 作为 LSOF_INCLUDE，需设置为 OHOS sysroot
3. dlsof.h 中 sockaddr_storage 重复定义：sys/socket.h 和 linux/socket.h（通过 linux/netlink.h 间接包含）都定义了该结构体
4. binary-sign-tool 签名失败："is not trust command"
5. lsof 运行受限，可能无法正常访问 /proc 文件系统

**当前状态**: Phase 2 完成，Phase 3 发现平台限制，需要记录为 partial 状态

**遗留问题**: 
1. lsof 在鸿蒙平台上的功能限制（/proc 文件系统访问）
2. 需要确定是否制作预编译包（功能受限但二进制可用）

---

## 四、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| lib/dialects/linux/Mksrc | shebang /bin/bash 不存在 | 改为 /!/data/service/hnp/bin/bash | 待生成补丁 |
| lib/dialects/linux/dlsof.h | sockaddr_storage 重复定义 | 添加 __OHOS__ 条件编译，定义 __kernel_sa_family_t，设置 _UAPI_LINUX_SOCKET_H | 待生成补丁 |

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

**编译结束**: 2026-04-25 21:27
**最终状态**: partial
