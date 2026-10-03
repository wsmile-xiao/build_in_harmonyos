# DRAFT — L1e 自测别破坏错目录：conan cache path 返回 export 而非包产物

> Status: **Draft**（待审核 promote）｜ severity: `2` | category: `conan|testing|methodology` | Updated: 2026-10-01
> 对应: `knowledge/drafts/DRAFT-tayga-0.9.2-conan-cache-path-l1e-sabotage.kv`

## 错误签名

```text
pkgdir=/root/.conan2/p/tayga78a6510e7047f/e        # 只有 conanfile.py/conandata.yml/conanmanifest.txt
sabotaged_test_exit=0 (expect NON-zero)             # "破坏后"测试仍通过
```

## 根因

Conan 2 中 `conan cache path tayga/0.9.2`（**不带 package_id**）返回的是配方 **export 目录**（`~/.conan2/p/<hash>/e`）。包的真实产物在 `~/.conan2/p/b/<hash>/p`，必须用带 package_id 的引用查询：

```text
conan cache path 'tayga/0.9.2:<package_id>'
```

对 export 目录 `rm bin/tayga` 是无害空操作（`rm -f` 静默成功），`conan test` 随后仍从完好的产物目录拿到二进制 → 误判为"假测试被实锤"。CI 的 L1e 破坏的是正确产物目录，不会误判——本机自测要对齐。

## 正确的 L1e 本机自测序列

```bash
conan create . --build=missing
# 取 package_id：JSON 顶层是 {revisions:{<rrev>:{packages:{...}}}}，递归查找最稳
PKGID=$(conan list 'tayga/0.9.2:*' --format=json | python3 -c "...(见 kv rec_command)")
PKGDIR=$(conan cache path "tayga/0.9.2:$PKGID")
ls "$PKGDIR"          # 必须能看到 bin/ 或 lib/，否则拿错了目录
rm -f "$PKGDIR/bin/tayga"
conan test test_package tayga/0.9.2   # 期望非零退出（Error 127）
```

## 判定规则

- 破坏前不 `ls` 确认产物在目标目录 → 自测无效
- "破坏后仍通过"先核破坏路径，再怀疑测试质量
- `Error 127`（命令找不到）= conanrun PATH 中二进制消失 = 测试真实依赖产物 ✅

## 来源

tayga/0.9.2 适配（2026-10-01）：L1e 自测首轮"失败"，追查发现删的是 export 目录；改用带 package_id 的 cache path 后自测通过，随后真机 CI L1 也 pass。

---
*本文由 `knowledge/drafts/DRAFT-tayga-0.9.2-conan-cache-path-l1e-sabotage.kv` 字段衍生（补齐 kv→md 配套）。*
