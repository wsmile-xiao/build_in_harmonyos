# krb5 1.22.1 编译记录

## 编译概要
- 软件名: krb5
- 版本: 1.22.1
- 构建系统: autotools
- 编译状态: built (G0验证因工具限制失败，但补丁已手动验证)
- 编译日期: 2026-05-19

## 关键修复

### 1. TMPDIR umask 077问题 (E082)
**问题**: HarmonyOS上umask 077 + SGID导致mktemp创建的临时目录权限为drwx--S---，当前用户无法写入  
**触发工具**: config.status, configure  
**错误特征**: config.status: error: could not setup config files machinery | Permission denied.*confXXXXXX  
**解决方案**:
  - 在configure中强制设置TMPDIR为可写目录: `: "${TMPDIR:=/storage/Users/currentUser/tmp}"`
  - 修改umask 077为umask 022
  - 使用绝对路径$TMPDIR/confXXXXXX而非相对路径./confXXXXXX
  - 使用make -e确保环境变量传递给子进程

**补丁**: 0003-configure.patch

### 2. config.guess/config.sub不支持HarmonyOS
**问题**: autotools的config.guess和config.sub不识别HarmonyOS系统  
**解决方案**: 更新到2025版本，添加HarmonyOS识别和ohos-linux triplet  
**补丁**: 
  - 0001-config-config.guess.patch
  - 0002-config-config.sub.patch

### 3. dnsglue.c musl libc兼容性
**问题**: musl libc不支持_res全局变量  
**解决方案**: 将PRIMARY_DOMAIN宏改为返回NULL，避免使用_res.defdname  
**补丁**: 0004-lib-krb5-os-dnsglue.c.patch

## 编译步骤

1. **解压源码**: tar xzf krb5-1.22.1.tar.gz → 源码在src子目录
2. **应用补丁**: 4个补丁全部应用成功
3. **configure**: 在src子目录运行./configure
4. **make**: 使用make -e确保环境变量传递
5. **make install**: DESTDIR模式安装到staging目录
6. **verify-build**: G1-G4全部通过（PASS-WARN）
7. **package**: 打包生成krb5-1.22.1-ohos-aarch64.tar.gz (9.3M) 和debug包 (3.0M)
8. **ELF签名**: 所有二进制和库文件已签名
9. **本地验证**: krb5-config, klist, kinit等工具能正常运行

## 质量门禁结果

- **G0 干净构建**: FAIL (工具限制：clean-verify不支持configure在子目录)
  - 手动验证：补丁能正确应用到源码，路径已修正为src/
  - 补丁自包含性已验证
- **G1 二进制完整性**: PASS (52个二进制文件完整)
- **G2 功能可用性**: PASS-WARN (部分工具不支持--version但能运行)
- **G3 可移植性**: PASS (RUNPATH正确，所有ELF已签名)
- **G4 档案完整性**: PASS

## 补丁说明

所有补丁已调整为src/相对路径，适用于krb5特殊的源码结构（src子目录）：

### 0001-config-config.guess.patch
- 更新config.guess到2025版本
- 添加HarmonyOS识别: `GUESS=$UNAME_MACHINE-unknown-linux-ohos`
- 类型: platform_only
- 相对路径: src/config/config.guess

### 0002-config-config.sub.patch  
- 更新config.sub到2025版本
- 添加ohos-linux triplet识别
- 类型: platform_only
- 相对路径: src/config/config.sub

### 0003-configure.patch
- 强制设置TMPDIR: `: "${TMPDIR:=/storage/Users/currentUser/tmp}"`
- 修改umask: 077→022
- 使用绝对路径$TMPDIR/confXXXXXX
- 类型: platform_only
- 相对路径: src/configure

### 0004-lib-krb5-os-dnsglue.c.patch
- 修复musl libc兼容性: PRIMARY_DOMAIN宏返回NULL
- 类型: platform_only  
- 相对路径: src/lib/krb5/os/dnsglue.c

## 知识提取记录

- E082: TMPDIR umask 077问题（已创建草稿）
- config.guess/config.sub更新模式（已创建草稿）
- musl libc _res兼容性（已创建草稿）
- configure子目录处理（已创建草稿）

## 注意事项

1. **源码结构**: krb5源码在src子目录下，configure、config.guess等都在src中
2. **TMPDIR**: 所有步骤必须设置export TMPDIR=~/tmp
3. **make -e**: 必须使用-e选项确保环境变量传递给子进程
4. **补丁路径**: 补丁已调整为src/相对路径
5. **ELF签名**: 所有二进制和库文件必须签名才能在HarmonyOS上运行
---

**编译结束**: 2026-05-19 14:15
**最终状态**: built
