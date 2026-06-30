# Perl Net::LibIDN

Perl XS 绑定模块，封装 GNU Libidn 库，提供 IDNA 域名编解码、Punycode 编解码和 Stringprep 字符串预处理功能。

## 编译指导

在 HarmonyOS/OpenHarmony 平台编译时需注意：

```bash
# 1. 确保 libidn 已安装到 /usr/local
#    (libidn.a + libidn.so.12 + 头文件)

# 2. 设置 LD_LIBRARY_PATH 以便 Makefile.PL 检测程序找到依赖库
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH

# 3. 生成 Makefile
perl Makefile.PL \
  --with-libidn=$HOME/usr/local/lib \
  --with-libidn-inc=$HOME/usr/local/include

# 4. 编译（补丁已自动注入 OTHERLDFLAGS 处理 OHOS 链接器问题）
make

# 5. 安装
make install DESTDIR=$TEST_PREFIX
```

### OHOS 链接器问题

OHOS 平台缺少 CRT 文件 (crti.o, crtn.o 等)，链接阶段会失败。通过补丁 `0001-Makefile.PL-ohos-linker.patch` 在 Makefile.PL 中注入 OTHERLDFLAGS：
- `-nostartfiles -nodefaultlibs -lc` 绕过缺失的 CRT 文件

### SELinux 限制

XS 模块 .so 文件在用户路径 (HMDFS, `hmdfs:s0`) 上无法被 Perl 加载，需要：
1. 使用 `binary-sign-tool` 签名 .so
2. 通过 HNP 包安装到 `/data/service/hnp/` (`hnp_file:s0`)

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [0.12-r17](./0.12-r17/) | published | 2026-06-29 |
