# E543: libdap 消费者构建三陷阱 (dap-config 打包缺陷 / autoconf 重生成 / _local 分支 segfault)

```
draft: E543-draft-GADA
status: pending-editor-review
title: "libdap 消费者构建三陷阱 (dap-config 重定位/autoconf 重生成/_local segfault)"
category: autotools, dependency-graph, portability, hmdfs
match_keywords: >
  Cannot find libdap, dap-config, AC_CHECK_LIBDAP, segfault request_dds, autoconf regenerate, touch -r, _local
error_signature: >
  Cannot find libdap|dap-config script could not be found|segfault.*request_dds|Segmentation fault.*Connect|Error relocating.*lld
root_cause: >
  libdap 3.20.x conan 包 bin/dap-config 打包缺陷 (prefix=/ 空 + 硬编码构建时 cache 路径);
  tar 旧时间戳 + patch 后 am--refresh 触发设备 autoconf 2.72 重生成 configure;
  libdap Connect 非 http 名字走 _local 分支 (d_http=0) 空指针解引用
rec_approach: >
  generate() 生成重定位 dap-config 注入 DAP_CONFIG + build() touch -r 拉平时间戳 +
  消费者测试用不可达 http URL 测错误路径
verification_cmd: >
  conan create archives/g/gadap/2.0.0 --name=gadap --version=2.0.0
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
  && grep GADAP_CONAN_TEST_PASS
solution: |
  见下文 "解决方案" 三件套 (配方 generate() 重定位 dap-config / build() 时间戳拉平 /
  测试用不可达 http URL)
fallback: |
  dap-config 重定位不可行时, 改为 CPPFLAGS/LIBS 直接注入 -I/-L 绕过
  AC_CHECK_LIBDAP 脚本探测
```

## 现象

libdap 3.20.x conan 包的下游消费者 (gadap 等 autotools + AC_CHECK_LIBDAP 软件) 构建时:

1. `configure: error: Cannot find libdap` / `The dap-config script could not be found` —
   dap-config 在 PATH 但版本/路径探测失败; 或找到了但输出的 `-I/-L` 指向 libdap
   **构建时**的 conan cache 路径, 消费者环境无效
2. make 阶段 configure 被重新生成 (autoconf 2.59 → 2.72), 此前对 configure 的
   补丁行号全部漂移, 且 E011 (config.status mktemp umask 077) 复发
3. 消费者测试程序调用 `Connect(本地路径)` + `request_dds()` → Segmentation fault

## 根因

1. libdap conan 包的 `bin/dap-config` 由上游 `configure --prefix=` 生成: prefix 为空,
   `-I/-L` 是 configure 探测到的**绝对路径** (libdap 构建沙箱内的 conan cache)。
   包被消费者安装后这些路径不再有效 — 与 libxml2 等包的 `.pc prefix=/` 同类打包缺陷
2. tar 解压保留 2008 年时间戳; `apply_conandata_patches` 更新 configure 后其 mtime
   变新, 但 `aclocal.m4`/`configure.ac` 保持旧时间; Makefile 的
   `$(top_builddir)/config.status: $(top_srcdir)/configure` 与
   `$(top_srcdir)/configure: $(am__configure_deps)` 规则判定过期 → 调
   `AUTOCONF` (设备上为 2.72) 重生成
3. libdap 3.20.6 `Connect::Connect`: 非 `http` 开头的名字走 `_local=true` 分支,
   `d_http=0`; 而 `request_dds/request_das` 无条件 `d_http->fetch_url(...)` —
   空指针解引用。**上游设计如此** (gadap/libdap 只支持 OPeNDAP 远程数据源)

## 解决方案

### 1. 配方 generate() 生成重定位 dap-config

```python
env = Environment()
env.define_path("DAP_CONFIG", os.path.join(self.generators_folder, "dap-config"))
```

重定位脚本内容按 `self.dependencies` 逐包拼接 (libdap 单独取
`include/libdap` + `lib`), `--version` 输出与 AC_CHECK_LIBDAP 的版本比较兼容。

### 2. build() 拉平时间戳防重生成

```python
anchor = os.path.join(self.source_folder, "configure.ac")
for rel in ("aclocal.m4", "configure", "Makefile.in", "config.h.in",
            "src/Makefile.in", "test/Makefile.in", "gadap-config.in"):
    p = os.path.join(self.source_folder, rel)
    os.utime(p, ns=(os.stat(anchor).st_atime_ns, os.stat(anchor).st_mtime_ns))
```

### 3. 消费者测试用不可达 http URL

`gadap_open("http://127.0.0.1:1/invalid.dds", &d)` → libdap 抛 `Error` →
gadap catch → 返回 `errval(GADAP_ERR_DAP_ERROR)`。完整验证 C++ 异常跨库边界
传播; 禁止用本地文件路径 (必 segfault)。

## 验证

```
conan create ... → test_package 7/7 断言 PASS (GADAP_CONAN_TEST_PASS)
```

## 关联

- libdap 配方的 .pc 运行时重写 (同源手法): archives/l/libdap/3.20.6/conanfile.py
- E011/E114 (config.status mktemp 陷阱): 见知识库对应条目
- 实例: archives/g/gadap/2.0.0/ (2026-09-05, 积分赛 feat/gadap-2)
