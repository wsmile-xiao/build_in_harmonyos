# perl-math-pari 2.030528-r1 编译记录

## 基本信息
- 软件名: perl-math-pari
- 版本: 2.030528-r1
- 类型: Perl XS/C 模块（PARI 数学库接口）
- 源码来源: CPAN (Math-Pari-2.030528.tar.gz)

## 编译过程

### 1. 源码获取
- Savannah 官方下载链接返回 404
- 从 CPAN 成功下载: https://cpan.metacpan.org/authors/id/I/IL/ILYAZ/modules/Math-Pari-2.030528.tar.gz
- 文件大小: 228KB

### 2. 配置阶段
**命令**:
```bash
perl Makefile.PL \
  INC="-I/storage/Users/currentUser/usr/local/include -I pari-2.3.5/src -I pari-2.3.5/src/headers -I libPARI" \
  PREFIX=/storage/Users/currentUser/usr/local
```

**说明**:
- 自动下载并配置 pari-2.3.5 库
- 处理器检测为 aarch64，使用 portable assembler-less build

### 3. CRT 文件缺失问题解决 ⚠️

**问题**: 链接阶段失败
```
ld.lld: error: cannot open crti.o: No such file or directory
ld.lld: error: cannot open crtbeginS.o: No such file or directory
ld.lld: error: unable to find library -lc
```

**原因**: OpenHarmony musl 不提供标准 CRT 启动文件

**解决**: 修改 Makefile 的 LDDLFLAGS（参考 Crypt-OpenSSL-Random 经验）
```bash
# 原始设置
LDDLFLAGS = -shared -O2 -fstack-protector-strong

# 修改为（第一次尝试，失败）
LDDLFLAGS = -shared -nostartfiles -nodefaultlibs -lc -O2 -fstack-protector-strong

# 最终方案（成功）
LDDLFLAGS = -shared -nostartfiles -L/storage/Users/currentUser/usr/local/lib -lc -O2 -fstack-protector-strong
```

**关键点**:
- `-nostartfiles` 跳过 CRT 启动文件
- `-L/storage/Users/currentUser/usr/local/lib` 指定 libc 库路径
- musl libc 位于 `/storage/Users/currentUser/usr/local/lib/libc.so`

### 4. 编译成功
- ✅ libPARI.a 静态库成功生成
- ✅ Pari.o 目标文件成功编译
- ✅ Pari.so (3.2MB) XS 模块成功链接
- ⚠️ 编译警告（65 个，无害）

### 5. 安装阶段
- ✅ 成功安装到 staging 目录
- ✅ 成功安装到本地 ~/usr/local

安装产物:
- `/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/aarch64-linux/auto/Math/Pari/Pari.so` (3.2MB)
- `/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/aarch64-linux/Math/Pari.pm`
- `/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/aarch64-linux/Math/PariInit.pm`
- `/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/aarch64-linux/Math/libPARI.pod`

## SELinux HMDFS 限制 ⚠️

**问题**: XS 模块无法加载
```
Can't load '.../Pari.so' for module Math::Pari: Permission denied
```

**原因**:
| 文件位置 | SELinux type | 加载结果 |
|---------|-------------|----------|
| `/data/service/hnp` | `hnp_file:s0` | ✅ 可加载 |
| `~/usr/local/lib` (HMDFS) | `hmdfs:s0` | ❌ Permission denied |

**解决方案**: 创建 HNP 包，管理员安装到系统目录

## 测试结果

### HMDFS 环境测试
- **模块加载**: ❌ Permission denied (SELinux 限制)
- **功能测试**: ⚠️ 无法执行（因加载失败）

### 编译质量验证
- **XS 模块**: ✅ ELF 格式正确，64-bit LSB arm64
- **链接完整**: ✅ libPARI.a 正确链接
- **平台适配**: ✅ CRT 问题已解决
- **产物大小**: 3.2MB (正常)

## XS 编译经验总结

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| CRT 文件缺失 | musl 无标准 CRT | `-nostartfiles -L/path -lc` |
| libc 找不到 | 默认路径不含 musl | 添加 `-L/storage/Users/currentUser/usr/local/lib` |
| SELinux 限制 | HMDFS domain 限制 | HNP 包安装 |

## 上库建议

1. **归档状态**: `built` (编译成功，功能受平台限制)
2. **发布方式**: 通过 HNP 包形式发布到 `/data/service/hnp`
3. **功能验证**: 需管理员协助在 HNP 环境中验证
4. **文档完整**: ✅ 编译过程已记录

## 参考
- Crypt-OpenSSL-Random 0.15 编译经验 (CRT 问题解决方案)
- OpenHarmony SELinux HMDFS 限制说明

---
**编译结束**: 2026-06-17 14:20
**最终状态**: built (编译成功，XS需HNP安装)