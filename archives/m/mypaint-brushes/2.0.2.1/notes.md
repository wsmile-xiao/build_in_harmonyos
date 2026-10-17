# mypaint-brushes 2.0.2.1 适配笔记

## 编译环境
- 构建系统: autotools (configure + make，纯数据包)
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4 (数据包无编译动作，仅文件复制)
- 状态: built → conan-verify 后 published

## 2026-09-24 复验修订（任务重发后）

原归档做于 2026-09-02，早于 SKILL v12.20（2026-09-03）新门禁。本次修订
对齐已合入纯数据包先例（kicad-demos 10.0.4 / linux-firmware-brcm）：

1. **package_type 显式声明 `"unknown"`**：原版刻意省略该属性以避免 L0k
   误判（注释自述），改为与先例一致的显式声明——纯数据包零可执行文件，
   非 application 且 bindirs 为空，不触发 R38 commands.json 要求。
2. **test_package 增加 C++ 消费者探针** `mypaint_brush_probe`（CMake 构建，
   消费 dep.cpp_info.resdirs 定位笔刷目录）：order.conf 条目逐一映射到磁盘
   .myb、全部 .myb 纯 JSON 配平校验、7 组目录齐全——与 kicad_demo_probe
   同款范式，补足"至少 1 个消费者用例"红线（原版仅 bash 脚本路径式校验）。
3. **package_id 清空**（self.info.clear()）：数据包内容与 settings 无关，
   先例同款。
4. manifest status → published（真机 conan create 全绿后回填）。
5. notes.md 原"注意事项"中 package_type="application" 描述与实际配方不符
   （R52 审计一致性风险），已更正。
6. **版本递增 2.0.2 → 2.0.2.1（R37）**：制品仓（cnb.cool）已有
   mypaint-brushes/2.0.2（9-02 归档曾被发布），同版本修订触发 R37
   409 Conflict（制品仓不支持同版本多 revision 并存）。按 CI 提示
   递增版本号后缀并同步 archives/ 目录（rapidjson 1.1.0.1 /
   any-lite 0.3.0.2 同款路径）。

（真机复验日志待验证后填写：conan create 输出、test_package 双路径结果、
消费者探针输出）

## 软件性质 (R38 决策依据)
mypaint-brushes 是 MyPaint 的**纯笔刷数据包**：brushes/*.myb (196 个笔刷文件)
+ order.conf (205 行，7 个笔刷组: Dieterle/classic/deevad/experimental/
kaerhon_v1/ramon/tanda) + mypaint-brushes-2.0.pc。零编译依赖、零编译产物、
无可执行文件 → **不需要 commands.json**（R38 库/数据类型）。数据安装路径为
$DATAROOTDIR/mypaint-data/2.0/brushes（注意是 mypaint-data 不是
mypaint-brushes，实测 staging 确认），pc 文件在 share/pkgconfig/。

## 编译步骤
1. W0: `bash ci/scripts/preflight_check.sh mypaint-brushes/2.0.2.1` → 通过（无依赖）
2. init-build（官方 URL: github mypaint/mypaint-brushes releases v2.0.2，
   sha256 实测 = 7984a74edef94571d872d0629b224abaa956a36f632f5c5516b33d22e49eb566，
   与 GitHub release 签名值一致）
3. R47 lang-preflight → detected=c（autotools），c↔cpp 兼容族，通过
4. `./configure --prefix=$DEFAULT_PREFIX`
5. `make -j2`（no-op: "Nothing to be done for 'all'"，数据包）
6. `make install DESTDIR=$TEST_PREFIX` → staging 396 个文件
7. `make check` → exit 0（"Nothing to be done for 'check'"，上游无测试目标）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 阶段 `config.status[700]: can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 拒绝写入 umask 077 创建的 owner-only (0700) 临时目录（config.status 内 `umask 077 && mktemp -d ./confXXXXXX`），内核级拒绝（python os.open 复现 Errno 13） | 知识图谱 E011 精确命中（xz/tar/wget 同模式）。方案: `sed -i 's/umask 077/umask 022/g' configure` 固化为 patches/0001（conandata.yml list 格式声明） |
| 2 | make -j2 警告 `jobserver mkfifo: Operation not permitted` | HMDFS 平台限制（mkfifo 系统调用受限），make 退化为串行但构建成功 | 平台限制记录，不阻塞 |
| 3 | SSL CERTIFICATE_VERIFY_FAILED（首次下载） | 环境 CA 证书未初始化 | `export SSL_CERT_FILE=/etc/ssl/certs/cacert.pem`；随后 init-build 自动安装 121 根证书成功 |

## 源码修改

- patches/0001-fix-configure-umask077-for-hmdfs.patch：configure 中 2 处
  `umask 077` → `umask 022`（config.status 临时目录创建段）。纯 autotools
  可移植性修改，无平台宏（R8-clean），知识条目 E011。

## 依赖版本

无依赖（零依赖纯数据包）。

## 验证结果

```bash
# 探索阶段 staging 校验（make install DESTDIR 后）
# staging: 396 files, share/mypaint-data/2.0/brushes/{7 组}/ + order.conf + share/pkgconfig/*.pc
order.conf <-> disk 互证: 196/196 条目均存在对应 .myb 文件
.myb 格式: 196/196 为纯 JSON（7b 开头, '{\n'），0 gzip（2.0 tarball 未压缩）
# test_package/test_mypaint_brushes.sh（R34 实质校验，7 项全过）:
ALL CHECKS PASSED: mypaint-brushes data package verification (R34 substantive)
```

## 注意事项

- 数据路径是 `share/mypaint-data/2.0/brushes`（mypaint-data！），
  package_info 用 `cpp_info.resdirs` 暴露，并附加
  `cpp_info.defines.append('MYPAINT_BRUSHES_DIR="<pkg>/share/mypaint-data/2.0/brushes"')`
  （与 pc 文件 Cflags 等价），`buildenv_info.append_path("PKG_CONFIG_PATH", .../share/pkgconfig)`。
- package_type="unknown"（R38 数据分支：无库无可执行，无需 commands.json；显式声明对齐 kicad-demos 10.0.4 先例），bindirs/libdirs/includedirs 置空，package_id 清空。
- order.conf 条目格式 `组/笔刷名#N`，磁盘文件 `组/笔刷名#N.myb`（#N 保留在文件名中）。
- 上游 v2.0.2 为最新正式 release（pre_json_brushes tag 是 prerelease，未采用）。
---

**编译结束**: 2026-09-02 23:59
**最终状态**: built
