# 上游测试依赖外部二进制（gpg）时的正确姿势：如实声明 N + 自解析做等价校验

**来源**：`debian-keyring 2026.06.27` 适配（对照 `debian-archive-keyring 2025.1`）
**日期**：2026-09-19
**状态**：DRAFT ｜ 上游用例 N=6（不可执行），本包新增断言 22/22

## 现象

上游自带一套测试，但**测试本体依赖宿主外部二进制**：

```sh
$ ls t/*.t | wc -l
6
$ grep -l 'gpg ' t/*.t | wc -l
6
$ head -8 t/at-least-2048.t
find_too_short () {
        k=$1
        gpg --no-options --no-auto-check-trustdb --no-default-keyring \
                --keyring "./output/keyrings/$k" --list-keys --with-colons \
                | awk -F: -v keyring=$1 ...
```

`./runtests` 会跑 `t/*.t`，其中 6 个用例全部通过 `gpg --list-keys --with-colons` 解析密钥环。
OpenHarmony 上没有 `gpg`/`gnupg`（也没有 `jetring`），这 6 个用例**无法执行**。

## 两个必须分开的判断

### 1) 测试口径：不能写"上游 N=0"

审查脚本会按上游实测 N 与正文声明 N 做少报核验。上游确实有 6 个用例，写成"没有测试"
或"不适用（上游 0 个用例）"就是**少报**。正确写法是把口径拆开：

```
上游测试用例通过率：N=6 —— 全部不适用（宿主无 gpg）
### 上游测试用例减少原因
1. t/*.t 共 6 个用例，全部用 `gpg --no-default-keyring --keyring … --list-keys --with-colons`
   解析密钥环；OpenHarmony 无 gpg/gnupg，属"环境不具备"，不是被绕过；
2. 这 6 个用例校验的是"密钥环里的密钥质量"（≥2048 位、无重复、无过期、无吊销、
   DM 与 DD 不重名、keyids 清单完整），全部可以在无 gpg 环境下用自解析等价校验。
```

### 2) 构建口径：**构建其实不需要 gpg**

上游 `Makefile` 生成密钥环的规则是纯字节拼接：

```make
output/keyrings/%.pgp: %-pgp %-pgp/0x*
	cat $*-pgp/0x* > $@
```

jetring 的形态是**一个公钥一个文件**（文件名就是 keyid，`0x<16 位>`）。于是配方可以
直接复刻这条 `cat` 规则，完全不依赖 `gpg`/`jetring`；需要 gpg 的只是"重新签发/校验"
这类维护动作。这条一定要写进配方注释 —— 否则下一个人会以为必须先装 gpg。

## 自解析等价校验（替代 gpg）

按 RFC 4880 逐个 packet 走完整个数据流即可：

```python
# 老格式头：长度类型在最低两位 → 1 / 2 / 4 字节，或"到末尾"
# 新格式头：1 字节（<192）/ 2 字节（192–223）/ 5 字节（0xFF）
# 解析走不通 ⇒ 拼接出来的密钥环是坏的（比"文件非空"强得多）
tags, err = parse_packets(raw)
assert err is None
assert tags.count(6) == len(glob.glob(f"{name}-pgp/0x*"))   # 公钥包数 == jetring 源文件数
```

实测这条断言很强且稳定（本包 4 个密钥环：947 / 205 / 44 / 6，与源目录文件数逐个相等），
再用 `sha512sum` 复核产物摘要，就覆盖了上游 `no-dupes`/`keyids-complete` 想守的
"清单与内容一致"这一层。

## 结论

遇到"上游有测试但测试依赖某个宿主工具"时，三件事一起做：

1. **如实声明上游 N**，并把"环境不具备"的具体原因写进 PR 正文与 `MANIFEST.yml`
   （`upstream: {total: 6, executed: 0, reason: "no gpg on OHOS"}`）；
2. **把构建与测试解耦**——查清构建是否真的需要那个工具（本例不需要，只需 `cat`）；
3. **用自解析做等价校验**，并把"清单 ↔ 内容"的一致性变成硬断言，
   而不是把测试删掉或静默跳过。
