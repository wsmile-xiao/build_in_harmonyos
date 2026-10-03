# libatasmart 0.19 — 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libatasmart(ATA S.M.A.R.T. 读取与报告库) |
| 版本 | 0.19(Debian orig libatasmart_0.19.orig.tar.xz,snapshot 归档取回) |
| 状态 | built |
| 构建系统 | autotools(tarball 自带 configure) |
| 源码 | https://snapshot.debian.org/archive/debian/20120523T094136Z/pool/main/liba/libatasmart/libatasmart_0.19.orig.tar.xz |
| sha256 | 61f0ea345f63d28ab2ff0dc352c22271661b66bf09642db3a4049ac9dbdb0f8d |

## 上游形态
- 纯 C 库(仅 libc;ATA passthrough 经内核 ioctl),无第三方依赖;
- 产物:lib/libatasmart.so.4(.0.5)+ include/atasmart.h + lib/pkgconfig/libatasmart.pc;
- 附带 skdump/sktest 诊断工具与 strpool host 工具。

## 配方设计(关键:交叉构建的 strpool 坑)
1. **strpool host 工具交叉坑**:Makefile 无条件 `make -C strpool strpool` 并执行它
   生成 atasmart.strpool.c——交叉构建时 strpool 被目标链(aarch64)编译、却要在
   构建机(x86_64)上执行,必挂("cannot execute binary file")。
   **tarball 已自带生成的 atasmart.strpool.c**,故最小解 = 补丁 0001:
   - `SUBDIRS = strpool .` → `SUBDIRS = .`(不编译 strpool);
   - `atasmart.strpool.c` 生成规则改 noop(echo using bundled);
   补丁对 Makefile.in 应用(patch -p1 回环验证一致),configure 在其后使用模板。
2. **零依赖**:仅 libc;configure 无 PKG_CHECK_MODULES,标准 autotools 链路即可。
3. **package**:make install 后清理 share/doc、share/man;保留 include/atasmart.h、
   lib/libatasmart.so.4、lib/pkgconfig/libatasmart.pc、share/vala/vapi(atasmart.vapi)。
4. **test_package**:C 消费者探针——`sk_disk_open("/dev/...不存在路径")` 断言返回负
   错误码且不崩溃,覆盖"库可加载、API 可调用、错误路径正确"三语义(不依赖真实硬盘)。

## 验证
- WSL 本机:configure RC=0 → make -j4 → libatasmart.so.4.0.5(未打补丁时 strpool
  被编译执行——host 构建无害;补丁后 make 复测通过且跳过 strpool)。
- OH CI:conan create(交叉)→ test_package 随本轮执行。

## 依赖
- 无(纯 libc)。

## 【知识库扩展】
- 见 knowledge/drafts/DRAFT-libatasmart-0.19-cross-strpool-noop-bundled-generated.kv/.md:
  "构建期 host 工具"交叉坑的 noop-bundled-generated 解法(与 appstream 工具包装法互补)。
