# testdisk 7.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **解压源码**
   ```bash
   tar xf testdisk-7.1.tar.bz2
   cd testdisk-7.1
   ```

2. **应用补丁**
   ```bash
   patch -p1 < 0001-.pre-scan-report.yaml.patch
   patch -p1 < 0002-config-config.guess.patch
   patch -p1 < 0003-config-config.sub.patch
   ```

3. **配置编译选项**
   ```bash
   CC=clang CXX=clang++ ./configure --prefix=/storage/Users/currentUser/usr/local --without-uuid --enable-missing-uuid-ok
   ```
   关键参数说明：
   - `--without-uuid`: 禁用 uuid 库支持（鸿蒙系统缺少 uuid-dev）
   - `--enable-missing-uuid-ok`: 允许在没有 uuid 的情况下继续编译
   - `--prefix`: 设置安装前缀

4. **编译**
   ```bash
   make -j2
   ```

5. **安装到测试目录**
   ```bash
   make install DESTDIR=/storage/Users/currentUser/test-install-testdisk-7.1
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | wget 下载时证书过期 | 使用 --no-check-certificate 或手动下载源码 |
| 2 | config.guess 不识别平台 | autotools 配置文件缺少 OpenHarmony 支持 | 应用补丁 0002-config-config.guess.patch |
| 3 | config.sub 不识别平台 | autotools 配置文件缺少 OpenHarmony 支持 | 应用补丁 0003-config-config.sub.patch |
| 4 | 临时目录权限问题 | /tmp 只读 | 使用 $TMPDIR 或 $HOME/tmp |
| 5 | ncurses 库路径问题 | ncurses 安装在非标准路径 | pkg-config 自动检测 |
| 6 | uuid 库缺失 | 鸿蒙系统缺少 uuid-dev | 使用 --without-uuid --enable-missing-uuid-ok 禁用 uuid |
| 7 | 编译器未指定 | 默认使用 gcc | 明确设置 CC=clang CXX=clang++ |

## 源码修改

### 补丁文件列表

1. **0001-.pre-scan-report.yaml.patch**
   - 类型: 自动生成
   - 内容: 预编译扫描报告，记录平台适配风险点
   - 平台专用: 是

2. **0002-config-config.guess.patch**
   - 类型: 自动生成
   - 内容: 修改 config.guess 以识别 OpenHarmony 平台
   - 平台专用: 是

3. **0003-config-config.sub.patch**
   - 类型: 自动生成
   - 内容: 修改 config.sub 以支持 OpenHarmony 目标平台
   - 平台专用: 是

## 依赖版本

| 软件名称 | 版本 | 是否必需 | 说明 |
|---------|------|---------|------|
| ncurses | 6.4.20221231 | 是 | 文本用户界面库，TestDisk 必需依赖 |
| clang | 系统默认 | 是 | C 编译器 |
| clang++ | 系统默认 | 是 | C++ 编译器 |

## 验证结果

```bash
# 检查编译产物
ls /storage/Users/currentUser/test-install-testdisk-7.1/storage/Users/currentUser/usr/local/bin/
testdisk  photorec  fidentify  qphotorec

# 检查可执行文件
/storage/Users/currentUser/test-install-testdisk-7.1/storage/Users/currentUser/usr/local/bin/testdisk --version
TestDisk 7.1, data recovery tool
```

## 注意事项

1. **uuid 缺失**: 鸿蒙系统缺少 uuid-dev 包，必须使用 `--without-uuid --enable-missing-uuid-ok` 参数
2. **平台识别**: 需要应用 config.guess 和 config.sub 补丁以正确识别 OpenHarmony 平台
3. **临时目录**: 如果遇到临时目录权限问题，设置 TMPDIR 环境变量
4. **测试限制**: 测试中检查 root 权限（geteuid()!=0），这是预期行为，不影响编译

---
**编译结束**: 2026-05-28 15:01
**最终状态**: built
---

**编译结束**: 2026-05-28 15:32
**最终状态**: built
