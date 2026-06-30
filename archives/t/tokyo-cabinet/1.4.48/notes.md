# 编译记录 — tokyo-cabinet 1.4.48

## 构建日志

### 2026-05-20

#### 第一阶段：源码获取
- 官方地址 (fallabs.com) 无法访问
- 从 Debian 镜像下载：https://deb.debian.org/debian/pool/main/t/tokyocabinet/tokyo-cabinet_1.4.48.orig.tar.gz
- 源码包大小：977KB，gzip 格式

#### 第二阶段：配置
- 初次 configure 失败，HMDFS 权限错误
- 错误信息：`./config.status: line 579: ./confXXXX/subs1.awk: Permission denied`
- 根本原因：HMDFS UID 映射问题，umask 077 导致临时目录无法写入
- 解决方案：`sed -i 's/umask 077/umask 022/g' configure`

#### 第三阶段：编译
- 编译器：clang
- 编译选项：-fPIC -O2
- 依赖：bzip2 1.0.8（已安装于 ~/usr/local/）
- 编译成功，有少量警告：
  - tcutil.c: 空语句警告（预期行为）
  - tctdb.c: 未使用变量警告（非关键）

#### 第四阶段：安装
- 安装位置：~/usr/local/
- 库文件：libtokyocabinet.a, libtokyocabinet.so.9.11.0
- 头文件：tcutil.h, tchdb.h, tcbdb.h, tcfdb.h, tctdb.h, tcadb.h
- 可执行文件：18 个工具（tcamgr, tchmgr, tcbmgr 等）

#### 第五阶段：后处理
- ELF 文件签名（OpenHarmony 执行要求）
- 符号链接替换为文件复制（HMDFS 不支持软链接）
- 设置 LD_LIBRARY_PATH 为 ~/usr/local/lib

#### 第六阶段：验证
- 功能测试：PASS（HDB、BDB、FDB 操作）
- 质量门禁 G1-G4：PASS

## 关键决策

1. **补丁创建**：创建 0001-fix-hmdfs-umask.patch 固化 configure 修改
2. **无需引导补丁**：标准 autotools，无需 OHOS 特定引导
3. **静态库为主**：主要产物为 libtokyocabinet.a，便于嵌入使用

## 参考资料

- E011：HMDFS umask/权限问题
- 相关技能：openharmony-compile-agent

## 后续事项

- 可考虑添加到软件包仓库
- 可作为 tokyo-tyrant 或其他 DBM 工具的依赖