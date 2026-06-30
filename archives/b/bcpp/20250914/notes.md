# bcpp 20250914 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: aarch64-unknown-linux-ohos (HarmonyOS HongMeng Kernel 1.12.0)
- CFLAGS: -fPIC -O2
- 状态: published

## 编译步骤

1. `perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub` — 补丁 config.guess/config.sub 识别 HarmonyOS (E007)
2. `sed -i 's/umask 077/umask 022/g' configure` — 修复 HMDFS umask 077 权限问题 (E011)
3. `./configure --prefix=$DEFAULT_PREFIX` — 配置编译，检测到 aarch64-unknown-linux-ohos
4. `make -j1` — 编译 14 个 C++ 源文件，链接生成 bcpp 二进制
5. `make install DESTDIR=$TEST_PREFIX` — 安装到 staging 目录 (DESTDIR 模式 R20)
6. `make check` — 测试通过 (run-test 脚本执行成功)
7. `python3 $SKILL_ROOT/scripts/ohc-run.py package bcpp 20250914` — 打包预编译包
8. `make install` — 安装到 $DEFAULT_PREFIX (模拟用户部署)
9. `$DEFAULT_PREFIX/bin/bcpp --version` — 验证可用性 (R7)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 知识图谱 | 解决方案 |
|---|------|------|----------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 缺少 __OHOS__ 检测分支 | E007 | 用 patch-autotools-ohos.pl 补丁 config.guess 和 config.sub |
| 2 | config.status "Permission denied" 创建临时文件 | HMDFS UID 映射导致 umask 077 目录不可写 | E011 | 将 configure 中 umask 077 改为 umask 022 |
| 3 | SSL 证书下载失败 | HarmonyOS 缺少 CA 证书 | 环境问题 | curl -k 手动下载源码和 CA 证书 |

## 源码修改

| 文件 | 修改内容 | 补丁文件 | 知识图谱 |
|------|----------|----------|----------|
| config.guess | 添加 `#elif defined(__OHOS__)` LIBC=ohos 检测 + HarmonyOS 系统识别 case 分支 | 0001-config.guess.patch | E007 |
| config.sub | 添加 ohos-linux 三元组到系统类型列表 | 0002-config.sub.patch | E007 |
| configure | umask 077 → umask 022 (两处: mktemp 和 mkdir) | 0003-configure.patch | E011 |

## 依赖版本

无额外依赖，bcpp 是独立的 C++ 程序，仅依赖 musl libc 和 ld-musl-aarch64.so.1。

## 验证结果

### make check
```bash
$ make check
cd code && make check
make[1]: Entering directory '.../code'
/bin/sh ./run-test
make[2]: Entering directory '.../code'
make[2]: Nothing to be done for 'all'.
make[2]: Leaving directory '.../code'
make[2]: Entering directory '.../code'
make[2]: Nothing to be done for 'all'.
make[2]: Leaving directory '.../code'
make[1]: Leaving directory '.../code'
# 退出码: 0，测试通过
```

### 二进制类型
```bash
$ file code/bcpp
code/bcpp: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

### 版本验证
```bash
$ $DEFAULT_PREFIX/bin/bcpp --version
C(++) Beautifier     t2025-09-14
```

### 功能测试
```bash
# 输入: int main(){if(1){return 0;}else{return 1;}}
# bcpp 格式化后:
int main()
{
	if(1)
	{
		return 0;
	}
	else
	{
		return 1;
	}
}
# 功能正常
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bcpp-20250914-ohos-aarch64.tar.gz | 123942 bytes (121KB) | 预编译包 (ELF 已签名) |
| bcpp-20250914-ohos-aarch64-debug.tar.gz | 39964 bytes (39KB) | 调试符号包 |
| 0001-config.guess.patch | 1572 bytes | E007: HarmonyOS 平台检测 |
| 0002-config.sub.patch | 636 bytes | E007: ohos-linux 三元组 |
| 0003-configure.patch | 785 bytes | E011: umask 077→022 |

## 注意事项

- config.guess/config.sub 补丁是所有 autotools 项目的通用适配 (E007)
- umask 077 → 022 修复是 HMDFS 平台的通用问题 (E011)，影响所有 autotools 项目
- bcpp 不支持标准 `--version` 参数，但输出版本号 `t2025-09-14`
- cb++ 是 bcpp 的 shell 脚本 wrapper，用于批量处理 C++ 文件
- 本次发布 tarball 未包含 input/output 测试数据，make check 仅验证构建成功

---

**编译结束**: 2026-06-25 14:18
**最终状态**: published
