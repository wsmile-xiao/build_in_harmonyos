# DRAFT-viewnior-1.8-l0i-utf8sig-remote-byte-corruption

远端 conanfile.py 经 contents-API 推送被精简/字节打乱 → L0i `utf_8_sig UnicodeDecodeError`(hint 误导向「带 BOM」);worker git-clone 挂为另一独立故障类别

## 现象

PR #15134(viewnior 1.8)多次构建失败,两类故障交替:

1. **构建 #79543(代码问题)** — `conan-build-test` 步骤 L0i 报:

```
[fail] L0i: conanfile.py AST 解析失败, 无法提取依赖:
  File "<frozen codecs>", line 322, in decode
  File ".../encodings/utf_8_sig.py", line 69, in _buffer_decode
    return codecs.utf_8_decode(input, errors, final)
[hint] 常见原因: conanfile.py 带 UTF-8 BOM 或语法错误。请以 UTF-8（无 BOM）重新保存
```

prepare/git-clone/checkout-pr/conan-setup 全 ✅,仅 conan-build-test ❌。
本地同配方同命令 CI 全绿(exit 0,L0/L1/L4/L5 pass),与 PR CI 矛盾。

2. **构建 #84446(worker 基础设施)** — `git-clone` 步骤失败:

```
stat: No such file or directory: .../build/.buildbot-patched
fatal: not a git repository (or any parent up to mount point /storage/Users)
```

git-clone/cleanup 全 ❌ 且 elapsedTime≈0,L0/L1 未执行,与代码无关。

## 根因

1. **远端 conanfile.py 与本地字节不一致(L0i 失败的根因)**:远端分支上
   `archives/v/viewnior/1.8/conanfile.py` 仅 13060B,是**注释/构建说明被剥离的精简版**
   (docstring 自述 "trimmed ... to keep the file small for the contents-API upload");
   本地完整版 17777B。`ci/conan/build_and_test.sh` 的 L0i 用 `encoding="utf-8-sig"`
   打开 conanfile.py 做 AST 提取依赖,远端字节损坏/精简后解码失败抛 UnicodeDecodeError,
   hint 误判为「带 BOM」——**实测本地无 BOM、UTF-8 正常**,根因在推送链路字节损坏
   (与 DRAFT-libkysdk-3.0.1.0 同族:contents-API 转码打乱文本文件)。
2. **worker git-clone 挂(第二类)**:worker 工作区 `.buildbot-patched` 缺失 +
   `fatal: not a git repository`,属 Worker 环境未正确就绪,与包内容无关。

## 最小判据(一行)

```
# 本地 utf-8-sig 解码正常但远端报 UnicodeDecodeError + 远端文件大小与本地不一致 → 命中本条
python3 -c "open('archives/v/viewnior/1.8/conanfile.py', encoding='utf-8-sig').read()"   # 本地 OK
wc -c <(curl -sL "https://raw.atomgit.com/{owner}/{repo}/blobs/<sha>/archives/v/viewnior/1.8/conanfile.py") archives/v/viewnior/1.8/conanfile.py  # 13060 vs 17777 = 不一致
```

## 推荐方案:push-clean-files-verify-bytes

1. 本地跑与 PR 完全相同的 `ci/conan/build_and_test.sh`(必须注入 `CI_BRANCH=feat/viewnior-1.8`
   与 `CI_PR_NUMBER`,否则 R40 静默跳过导致「本地过、CI 挂」),确认本地配方正确;
2. 用本地干净文件经 contents API `PUT` 覆盖远端精简/损坏版——必须带
   `branch=feat/viewnior-1.8`(放 body,放 query 会 404 "Blob Not Found")+ `sha`(旧 blob)+
   `content`(base64,**零空格**);
3. 推送后**字节级对比**远端 raw 与本地(`cmp` 应无输出),确认转码不再发生;
4. 再触发 `/rebuild`(worker 故障则等 worker 恢复后重试)。

## 禁止事项

- ❌ 对 `utf_8_sig UnicodeDecodeError` 按 hint「带 BOM」处理(实测无 BOM,加 BOM 反而更糟);
- ❌ 对远端文件损坏反复 `/rebuild`(确定性失败,须先 PUT 覆盖远端字节);
- ❌ contents-API PUT 不带 `branch`(404 Blob Not Found,默认落 main 找不到该文件);
- ❌ base64 content 含空格(截断解码)。

## 关系

- similar_to: DRAFT-libkysdk-3.0.1.0-contents-api-byte-corruption-binary-patch-diff(字节损坏同族,本类表现为 L0i 解码失败而非 checkout-pr binary patch)、DRAFT-libfprint-1.94.10-contents-api-truncated-conanfile-empty-package(截断同族,本类未截断到缺方法,但字节已不一致)
- 适用原则: W2(PR 原子性)、W3(本地编译验证)

---
*由 viewnior 1.8 PR #15134(构建 #79543 L0i utf_8_sig + #84446 worker git-clone)修复过程沉淀,2026-10-11*
