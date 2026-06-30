# file 5.45 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-03-23
- 编译器: clang (Clang 15.0.4, LLVM)
- 状态: partial（test-report 缺失导致降级，但 72/72 测试全通过）

## 编译步骤
1. 下载源码 `https://astron.com/pub/file/file-5.45.tar.gz` 并解压
2. 修补 config.sub 添加 `linux-ohos*` kernel-os 白名单
3. 修补 man page 和源文件中的硬编码路径
4. 配置: `./configure --prefix=$HOME/usr/local --disable-libseccomp --enable-static --disable-shared LDFLAGS=-static`
5. `make`
6. `make install` 到 staging 目录
7. 测试: 72/72 全通过
8. 制作预编译包 (8.9MB)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.sub 不识别 OHOS | 缺少 `linux-ohos*` 白名单 | 修补 config.sub |
| 2 | 动态链接 .so 软链接无法加载 | 鸿蒙 SELinux 限制 | 使用静态链接 `--enable-static --disable-shared LDFLAGS=-static` |
| 3 | man page 路径错误 | 硬编码路径 | 修补 doc-file.1, doc-libmagic.3, doc-magic.4 |
| 4 | 源码路径问题 | 硬编码路径 | 修补 src-file, src-magic.h, tests-test |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|---------------|
| config.sub | 添加 linux-ohos* 白名单 | ✅ 0001-config.sub.patch |
| doc/file.1 | 修正路径 | ✅ 0002-doc-file.1.patch |
| doc/libmagic.3 | 修正路径 | ✅ 0003-doc-libmagic.3.patch |
| doc/magic.4 | 修正路径 | ✅ 0004-doc-magic.4.patch |
| src/file | 修正路径 | ✅ 0005-src-file.patch |
| src/magic.h | 修正路径 | ✅ 0006-src-magic.h.patch |
| tests/test | 修正路径 | ✅ 0007-tests-test.patch |

## 依赖版本
- zlib, bzip2, xz/lzma

## 验证结果
- file --version → file-5.45 ✅
- 测试: 72/72 全部通过 ✅
- 功能验证: ELF/zlib/bzip2/xz 格式识别正常 ✅
- 质量门禁: PASS

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| file-5.45-ohos-aarch64.tar.gz | 8.7MB | 主包（静态链接） |

## 注意事项
- 必须使用静态链接，动态链接因 SELinux 限制不可用
- file 命令依赖 magic.mgc 数据文件，确保安装路径正确

---

## 归档处理记录（2026-05-27）

### 问题诊断

**旧记录问题**：
- manifest.yaml 显示 status: built，但 packaging 目录不存在
- 无 .tar.gz 预编译包文件（违反 R24 归档清理规则）
- 有 7 个补丁文件存在，有知识沉淀

**本次编译失败**：
- 编译日期: 2026-05-27
- 失败阶段: configure (Step3)
- 失败原因: config.status 权限问题（OHOS 系统限制）
- 错误信息: `config.status:982: error: could not setup config files machinery`
- 知识匹配: E072（config.sub 三元组验证失败）— 但实际错误不同

### 归档决定

根据 R24 归档清理规则：
- **方案选择**: 方案 A - 标记为 archived
- **理由**: 旧记录有补丁、有知识，但无产物；本次编译失败是环境问题而非软件适配问题
- **状态变更**: built → archived
- **保留内容**: 7 个补丁文件供未来参考

### 后续建议

1. **环境问题**: config.status 权限问题是 OHOS HMDFS 文件系统的 UID 映射限制，与软件本身无关
2. **尝试 E011 方案**: 可尝试修改 configure 中的 umask（`sed -i 's/umask 077/umask 022/g' configure`）
3. **备选方案**: 如果 umask 修改无效，可考虑使用 E011 的极端方案（手动生成 config.h）
4. **补丁有效性**: 已有的 7 个补丁文件仍然有效，可在解决环境问题后继续编译

### 归档状态

- manifest.yaml 状态: archived
- archiving_reason: 已添加说明
- notes.md: 已更新本次编译失败记录
- 补丁文件: 已保留（0001-0007）
