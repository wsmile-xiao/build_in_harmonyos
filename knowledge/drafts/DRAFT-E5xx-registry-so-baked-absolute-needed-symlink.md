# DRAFT: 制品仓 so 烙印绝对路径 NEEDED 的 symlink 修复（保签名）

## 场景

下游包链接制品仓的共享库链（如 gd → libfontconfig.so.1），本地构建测试全绿，但 CI worker 上测试运行期报：

```
Error loading shared library /storage/Users/currentUser/.conan2/p/expat9fb72708ad085/p/lib/libexpat.so: (needed by /storage/Users/currentUser/.cache/conan2/p/fontc9e10589207d96/p/lib/libfontconfig.so.1)
```

## 根因（三层）

1. **烙印**：制品仓部分二进制包的 DT_NEEDED 是发布机 conan 缓存的**绝对路径**（实例：fontconfig/2.18.1 的 libfontconfig.so.1 需要 `/storage/.../.conan2/p/expat…/lib/libexpat.so`）。
2. **缓存布局差异**：CI worker 的 conan 缓存在 `$HOME/.cache/conan2`，烙印路径不存在 → musl loader 按路径解析失败；**LD_LIBRARY_PATH 无法补救绝对路径 NEEDED**（只对 soname 搜索生效）。
3. **代码签名约束**：用 patchelf 改写 NEEDED 为 soname 的常规思路在 OHOS 不可行——内核对 so 做代码签名校验，修改过的副本加载直接 `Permission denied`（实测：dlopen 补丁版复现，dlopen 原版成功，两文件仅 78KB section 布局差异）。

## 方案：保签名的 symlink

build() 阶段（测试运行前）：

1. 扫描依赖图全部 .so 的 DT_NEEDED（readelf -d 或内嵌 ELF 解析器）
2. 收集"绝对路径 且 本地不存在"的 NEEDED 条目
3. 对每个缺失路径：从依赖图找同名（basename）真实库 → `mkdir -p 父目录 && ln -s 真实库 烙印路径`

原理：symlink 指向真实文件，**文件内容不变 → 代码签名有效**；loader 按绝对路径打开 symlink → 加载成功（实测 dlopen 验证）。

配套：测试命令内联注入**全依赖链** LD_LIBRARY_PATH（`self.dependencies.values()` 遍历所有 libdir——conanbuild 环境只带直接依赖，传递依赖如 expat/libtiff 缺失时同样报错）。

边界：只创建调用用户 HOME 树内路径、仅缺失时创建（幂等）；跨机器包目录短 hash 一致（同一配方+配置），CI/本地路径可对齐。

## 失败案例（nagios 4.5.14 PR #9573 实测）

- 轮 1（#44394）/ 轮 2（#44432）：libexpat 绝对路径加载失败，615cgierror 3 断言 + 618cgisecurity 1 断言 FAIL
- 修复后轮 4（#44436）：全绿

## fallback

- 烙印路径不可写（非 HOME 树）：只能规避该依赖
- 根因修复：上游包重新发布（打包机链接时禁用绝对路径，或发布流程统一缓存路径）

## 验证

- PR #9573 CI #44436 绿
- 本地模拟（移走烙印目录 + symlink 指向新位置）：statusmap.cgi 正常运行
