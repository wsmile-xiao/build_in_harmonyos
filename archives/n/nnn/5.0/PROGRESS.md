# nnn 5.0 — 编译进度

> 档案创建时间: 2026-04-28 00:00:00
> 最后更新: 2026-04-28 (当前状态)

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | nnn |
| 版本 | 5.0 |
| 状态 | ⚠️ partial（签名失败，但功能可用） |
| 构建系统 | Makefile（简单 Makefile，无 configure） |
| 源码路径 | gitee.com/mirrors/nnn.git (v5.0) |

## 二、编译阶段（checkbox 实时更新）

### Phase 1: 环境准备
- [x] 源码下载（从 Gitee 镜像克隆）
- [x] 依赖安装（musl-fts 1.2.7, readline 8.2, ncursesw 6.4）

### Phase 2: 编译（直接 make）
- [x] make 编译完成
- [x] 手动安装完成（DESTDIR 模式，由于缺少 install 命令）

### Phase 3: 测试验证
- [x] 功能测试：nnn -V 输出 "5.0"，功能正常
- [x] 依赖验证：libreadline.so.8, libc.so 已满足

### Phase 4: 预编译包制作
- [x] 收集产物（nnn, nnn.1）
- [x] Strip 二进制（从 362K 减小到 306K）
- [x] 创建 install.sh
- [x] 打包 tar.gz（330K）
- [⚠️] ELF 签名失败（binary-sign-tool 报 "not trust command"）

### Phase 5: 归档收尾
- [x] 预编译包制作完成
- [⚠️] 签名未完成（平台限制，记录为已知问题）

## 三、对话记录

### 对话 #1 — 2026-04-28
**操作**: 
1. 加载 openharmony-compile-agent skill
2. 从 Gitee 克隆 nnn v5.0 源码
3. 安装依赖：musl-fts 1.2.7, readline 8.2（预编译包）
4. 编译：make PREFIX=~/usr/local CFLAGS/LDFLAGS/LDLIBS 配置
5. 手动安装（缺少 install 命令）
6. 验证：nnn -V 输出 5.0
7. 打包：nnn-5.0-ohos-aarch64.tar.gz (330K)

**结果**: 编译成功，功能可用，但 ELF 签名失败

**发现的问题**:
1. GitHub/GitCode 下载超时 → 使用 Gitee 镜像解决
2. 缺少 fts.h 和 readline → 使用预编译包安装
3. 链接错误：ncursesw 和 readline 需正确链接 → LDLIBS 配置
4. 缺少 install 命令 → 手动 cp 和 chmod
5. ELF 签名失败 → 记录为平台限制，功能仍可用

**当前状态**: 编译完成，预编译包已制作，签名失败但可分发

**遗留问题**: ELF 签名问题需要平台支持解决

## 四、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| 无 | 无需修改源码 | 编译参数调整 | 无补丁 |

## 五、预编译包交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| nnn-5.0-ohos-aarch64.tar.gz | 330K | 预编译包（未签名） |
| nnn | 306K | 主程序二进制（stripped） |
| nnn.1 | 20K | 手册页 |
| install.sh | 1K | 安装脚本 |

## 六、编译参数记录
```bash
# 编译命令
make PREFIX=~/usr/local \
    CFLAGS="-I~/usr/local/include -I~/usr/local/include/ncursesw" \
    LDFLAGS="-L~/usr/local/lib" \
    LDLIBS="-lreadline -lncursesw -lfts -lpthread"

# 依赖库
- ncursesw 6.4（已编译为静态库 --without-shared）
- readline 8.2（预编译包）
- musl-fts 1.2.7（预编译包）
```

## 七、结束记录
- **最终状态**: partial（签名失败，功能可用）
- **结束时间**: 2026-04-28
- **备注**: 预编译包可分发，但需用户手动确认执行权限（首次运行）