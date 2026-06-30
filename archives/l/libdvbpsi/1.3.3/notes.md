# libdvbpsi 1.3.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化: `python3 ohc-run.py init-build libdvbpsi 1.3.3`
2. 配置: `./configure --prefix=$DEFAULT_PREFIX`
3. 编译: `make -j1`
4. 安装（staging）: `make install DESTDIR=$TEST_PREFIX`
5. 安装（本地）: `make install`
6. 打包: `python3 ohc-run.py package libdvbpsi 1.3.3`
7. 收尾: `python3 ohc-run.py finish libdvbpsi 1.3.3 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `Invalid configuration '[]'` | manifest.yaml `configure_options: []` 被 clean-verify 正则解析为字面 `[]` 字符串传入 configure | 将 `configure_options: []` 改为 `configure_options:`（空值） |
| 2 | config.guess 不识别 HarmonyOS | 2017 版 config.guess 缺少 HarmonyOS 检测分支 | 修补 config.guess 添加 HarmonyOS 支持 |
| 3 | config.sub 不识别 linux-ohos 三元组 | config.sub 缺少 ohos 映射和白名单 | 修补 config.sub 4处修改（kernel-os白名单、ohos-linux映射、OS白名单、linux-ohos例外） |
| 4 | configure 中 mktemp -d 权限不足 | HMDFS setgid 目录继承导致 umask 077 创建的临时目录权限不足 | 修补 configure 将 umask 077 改为 umask 007 |

## 源码修改

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| 0001-.auto-config.guess.patch | .auto/config.guess | 添加 HarmonyOS 检测分支 |
| 0002-.auto-config.sub.patch | .auto/config.sub | 4处修改支持 linux-ohos 三元组 |
| 0003-configure.patch | configure | umask 077→007（解决 HMDFS mktemp 权限问题） |

## 依赖版本

无额外依赖，纯自包含库。

## 验证结果

- DESTDIR install: PASSED
- 产物: libdvbpsi.a (静态库), libdvbpsi.so.10.0.0 (共享库)
- 头文件: 78+ header files in include/dvbpsi/
- pkgconfig: libdvbpsi.pc
- G0 clean-verify: PASS（补丁自包含）
- G1-G4 verify-build: PASS

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libdvbpsi-1.3.3-ohos-aarch64.tar.gz | 1.3MB | 预编译包（含 ELF 签名） |
| libdvbpsi-1.3.3-ohos-aarch64-debug.tar.gz | 187KB | debug 符号包 |

## 功能测试（2026-06-03 补充）

### API 级测试 (13项全部通过)

| # | 测试项 | 结果 |
|---|--------|------|
| 1 | Handle create/delete | PASS |
| 2 | Descriptor 创建/添加/链表/销毁 | PASS |
| 3 | PSI Section 创建/销毁 | PASS |
| 4 | PAT 初始化+生成 (CRC=0xD6DBB9D8) | PASS |
| 5 | PMT 初始化+ES添加+生成 | PASS |
| 6 | BCD8→Uint32 转换 | PASS |
| 7 | 100个描述子内存压力测试 | PASS |
| 8 | 多 PSI Section 链式管理 | PASS |
| 9 | CanDecodeAsDescriptor 匹配/不匹配 | PASS |
| 10 | PMT descriptor add | PASS |
| 11 | PAT 动态分配 new/delete | PASS |
| 12 | PMT 动态分配 new/delete | PASS |
| 13 | 共享库符号导出验证（6大API族） | PASS |

- 静态库链接测试: PASS（直接用 libdvbpsi.a 编译运行 13/13 通过）
- 共享库链接测试: PASS（LD_LIBRARY_PATH 模式运行 13/13 通过）

### 库属性

- 导出函数: 278个 (nm -D grep " T ")
- 头文件: 78个
- 依赖: 仅 libc.so
- RUNPATH: $ORIGIN:$ORIGIN/external

## 注意事项

- 这是纯库软件，无命令行二进制，G2 functional 门禁报告 ⚠️1（无二进制可验证）
- configure_options 在 manifest.yaml 中必须用空值格式（`configure_options:`），不能用 YAML 空列表语法（`configure_options: []`），否则会被 clean-verify 正则解析为字面字符串传入 configure
- pkg-config 需设置 PKG_CONFIG_PATH 包含 ~/usr/local/lib/pkgconfig

## 知识提取

- ✅ HMDFS setgid umask 问题 → ref: E011
- ✅ 2017 版 config.guess 不支持 GUESS= → ref: E007
- ✅ config.sub linux-ohos 4处修改 → ref: E072

---

**编译结束**: 2026-06-03 10:16
**最终状态**: built
