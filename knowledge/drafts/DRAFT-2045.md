# DRAFT-2045：HMDFS 上共享库 SONAME 兼容名实体化

> Contributor: xuguowei | Status: Draft | Updated: 2026-08-12
> Source: libtorrent 0.16.17 HarmonyOS PC adaptation, Issue #2045

## 现象

Libtool 通常安装一个真实的版本化共享库，并通过符号链接提供开发名称和 SONAME 名称：

```text
libtorrent.so       -> libtorrent.so.47.0.0
libtorrent.so.47    -> libtorrent.so.47.0.0
libtorrent.so.47.0.0
```

HarmonyOS 设备的 HMDFS 工作目录不支持创建 symlink。安装阶段若无替代处理，可能缺少
`libtorrent.so` 或 `libtorrent.so.47`，从而使下游链接或运行时加载失败。

## 与现有知识的关系

- `E274` 正确说明了 SONAME 兼容名称缺失的风险，但其首选方案是创建 symlink，不能在
  HMDFS 上无条件执行。
- `E316` 已验证可通过复制真实 ELF 来补齐 SONAME 实体，但记录的是 R/OpenBLAS 的移动包场景。
- libtorrent 0.16.17 提供了独立的 Libtool 证据：安装后以普通文件副本提供
  `libtorrent.so` 和 `libtorrent.so.47`，真实库为 `libtorrent.so.47.0.0`。

因此本草稿建议修订 `E274` 的适用边界，并用 libtorrent 证据扩展 `E316` 的通用性，
不申请重复的新知识编号。

## 方案

1. 在支持 symlink 的文件系统上保留上游标准链接布局。
2. 在 HMDFS 等不支持 symlink 的文件系统上，定位最终真实版本化 ELF。
3. 将该 ELF 复制为开发名称和 SONAME 名称；不要只复制 `lib*.so`。
4. 删除不可重定位的 Libtool `.la` 元数据。
5. 使用 `llvm-readelf -d` 核对 SONAME，并在隔离运行时搜索路径下构建和运行真实消费者。

示意命令：

```sh
cp libtorrent.so.47.0.0 libtorrent.so.47
cp libtorrent.so.47.0.0 libtorrent.so
llvm-readelf -d libtorrent.so.47.0.0 | grep SONAME
```

兼容名称应从安装结果或 ELF SONAME 推导，不能把其他库的 ABI 版本硬编码到通用逻辑中。

## 验证证据

libtorrent 0.16.17 在 HarmonyOS aarch64 真机完成单包 shadow CI：

- L0、L1、L4、L5 通过；L2 因库包无 `bin/` 正常跳过。
- 7/7 个上游测试程序通过，151 个测试实际通过。
- 1 个只验证 symlink 回调路径的测试按平台能力豁免，同程序其余 27 个目录事件测试继续执行。
- Conan `test_package` 1/1 通过，验证安装后公共 API、bencode 往返和 SHA-1。
- 包中存在 `libtorrent.so.47.0.0` 以及 `libtorrent.so`、`libtorrent.so.47` 普通文件兼容副本。

## 禁止做法

- 不要在 HMDFS 上无条件调用 `ln -s` 或 `os.symlink()`。
- 不要只复制开发名称而遗漏 ELF NEEDED 所要求的 SONAME 名称。
- 不要因一个 symlink 专用测试不可执行而跳过整个文件系统测试程序。
