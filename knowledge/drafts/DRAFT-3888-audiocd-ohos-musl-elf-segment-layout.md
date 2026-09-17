# DRAFT-3888-audiocd: OHOS musl loader 拒绝多 RW LOAD 段布局

> 来源：audiocd 26.04.3 适配（平台任务 #3888）。症状与既有 E488/E502/E517
> （权限/签名/拷贝类）相同，但根因是 ELF 段布局——独立根因分支。

## 症状

```
Error loading shared library /path/to/libfoo.so: Permission denied
```

- dlopen 或程序启动时对某个 .so 报 "Permission denied"
- `ls -la` 权限正常（777/770）、文件可读（`head -c 4` 得 ELF 魔数）
- 同目录、同权限的兄弟库能正常 dlopen
- chmod 777 无效（HMDFS 上 chmod 本来也不生效，E046）
- musl 报错不带 errno 细节，极易被误判为文件系统权限问题

## 根因

OHOS musl 动态加载器拒绝 mmap 特定 ELF program header 布局：多个高址 RW
LOAD 段（.dynsym/.note.ohos.ident/.dynstr 被拆进 VirtAddr 0x10000/0x20000/
0x30000 的独立 RW 段，Align 0x10000）。

两个独立来源：

| 来源 | 机制 | 实测 |
|---|---|---|
| lld 默认 max-page-size=0x10000 | 动态段条目较多时以 64K 页对齐拆分段表 | audiocd 的 libaudiocdplugins.so：7 LOAD |
| OHOS patchelf --replace-needed | 修改 dynamic 段时按 0x10000 页重排 program header | 4 LOAD/27KB → 7 LOAD/198KB |

注意 `patchelf --page-size 4096` 只控制文件膨胀（198KB→38KB），段数不变
（仍 7 段），照样被拒。

## 30 秒诊断

```bash
readelf -lW libfoo.so | grep -cE '^  LOAD'
# 4 → 常规布局，问题在别处（查 E488/E502/E517 权限/签名类）
# 5+（含高址 RW Align 0x10000 段）→ 本条目
```

最小 dlopen 探针（交叉编译一个 8 行的 dlopen 程序）可以进一步确认
"同权限 KCddb6.so 能开、被破坏的 audiocdplugins.so 不能开"的对照。

## 修复

**链接期预防**（Conan 配方 generate()）：

```python
tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = "-Wl,-z,max-page-size=0x1000"
tc.variables["CMAKE_MODULE_LINKER_FLAGS_INIT"] = "-Wl,-z,max-page-size=0x1000"
```

**打包期止损**：不要对最终 .so 跑 `patchelf --replace-needed` 做 R05
relocatable sweep——绝对路径 DT_NEEDED 在 CI 一致的 conan 缓存布局下可
加载（libkcddb 26.04.3 已合入先例，其发布的 libKCddb6.so 就保留着
`/storage/.../.conan2/p/.../libKF6ConfigGui.so` 绝对路径 NEEDED）。

## 验证

audiocd/26.04.3（package_id 08149eb3890c4b1d2687a38b0ed16edb39e899dd）：
- 加 max-page-size=0x1000 后 libaudiocdplugins.so 为 4-LOAD 布局，dlopen 探针 OK
- test_package 35/35 断言 ALL PASS（含 QLibrary 加载全部 5 个编码器插件）
- 对照实验：同文件经 patchelf --replace-needed 处理三次后变 7-LOAD/198KB，
  dlopen 立即 "Permission denied"

## 与既有条目的关系

- E488（hmdfs dlopen Permission denied）：权限模型根因，copy-rewrite 修法——症状同、根因不同
- E502（musl dlopen Permission denied probe-then-route）：签名/发布态根因——症状同、根因不同
- E517（codesign 失效）：签名根因——症状同、根因不同
- 本条：**ELF 段布局根因**（链接器/patchelf 产生），修法是链接 flag 与禁用 sweep——全新分支

## 波及面

- 任何用 OHOS clang/lld 链接共享库且运行时 dlopen/NEEDED 加载的配方
- 所有做 R05 patchelf sweep 的既有配方（潜在风险：sweep 后的包在某些加载路径下被拒）
