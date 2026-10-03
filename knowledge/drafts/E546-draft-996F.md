# E546 — L4 把补丁说明里的英文单词误报为危险函数

> Draft（待知识库主编审核 promote）｜对应: `knowledge/drafts/E546-draft-996F.kv`
> 来源包：spinner/1.2.4（修 CI 构建 #66196 时本地门禁命中）

## 错误特征

补丁的 hunk 里**根本没有**任何危险函数，但 L4 报 warn：

```
[warn] L4: Dangerous functions found in patches:
archives/s/spinner/1.2.4/patches/0001-configure-hmdfs-umask.patch
L4_RESULT=warn: dangerous functions in patches
```

定位命中的具体位置：

```bash
grep -noE '(strcpy|sprintf|gets|strcat)\b' patches/0001-configure-hmdfs-umask.patch
17:gets
```

第 17 行是补丁说明里引用上游 make 报错的那句：

```
"No targets specified and no makefile found".
                 ^^^^^^ "tar" + "gets"
```

## 触发条件

- 构建系统: 任意（与构建无关，是**门禁扫描**问题）
- 阶段: testing（L4 静态安全扫描）
- 前提: `patches/*.patch` 带人类可读说明头（commit-message 式前言），
  且说明里出现 `target(s)` / `budgets` / `strategies` 等内嵌 `gets` 的英文单词，
  或引用了含 `strcat`/`sprintf` 的构建输出

## 根因分析

CI 的 L4 门禁实现是**无上下文**的文件级扫描：

```bash
DANGER=$(grep -rlE '(strcpy|sprintf|gets|strcat)\b' "$PATCH_DIR" 2>/dev/null || true)
```

两个问题叠加：

1. `grep -r` 扫的是 `patches/` 下**所有文件的全部行**，补丁的说明前言与
   diff hunk 同样被扫——说明头本应被排除，但正则并不区分二者；
2. `\b` 只是断言"前一字符不是词字符"，**不要求整词命中**。`tar` 与 `gets`
   之间没有词字符，所以 `"tar` + `gets` `specified"` 被判定为一次 `gets` 命中。

于是"为了说明问题而引用报错原文"这个善意动作，反而触发了安全告警。
注意 L4 是 **warn 而非 fail**（不影响 rc=0），但会在 PR 评论里留下
"发现危险函数"的误导性报警报。

## 解决方案

### 推荐方案

只改写**说明里的措辞**，避开内嵌子串，**hunk 内容一字不动**：

```diff
-and no Makefile is produced, so the following `make` aborts with
-"No targets specified and no makefile found".
+and no Makefile is produced, so the following make run aborts because there
+is no makefile for it to read.
```

复扫必须无输出：

```bash
grep -rlE '(strcpy|sprintf|gets|strcat)\b' <pkg>/patches   # 期望无输出
```

同时严格验证补丁仍能干净应用（防止改说明时破坏 hunk）：

```bash
patch -p1 --fuzz=0 --dry-run < <pkg>/patches/0001-xxx.patch   # 必须 DRY-RUN OK
```

### 禁止做法

- ❌ 在补丁说明里直接写 `strcpy`/`sprintf`/`gets`/`strcat` 来"声明我没用到它们"
  —— 说明文字同样被扫，写出来就触发 warn
- ❌ 为绕过 L4 而删掉 `patches/` 目录或改动 hunk 行 —— 这是为迎合误报破坏真实修复，
  会让适配回退到原本的失败状态

### 回退方案

让 `.patch` 文件只包含裸 unified diff，说明文字挪到 `manifest.yaml` / `notes.md`：

```bash
diff -u a/configure b/configure > patches/0001-configure.patch
```

代价是补丁自解释性变差（CI/审阅者看不到意图），所以排在推荐方案之后。

## 验证

```bash
# 复现定位
grep -rlE '(strcpy|sprintf|gets|strcat)\b' <pkg>/patches
grep -noE '(strcpy|sprintf|gets|strcat)\b' <pkg>/patches/*.patch

# 修复后应无输出，且 L4 报 "patches clean"
CI_PACKAGES="archives/<字母>/<包>/<版本>" zsh ci/conan/build_and_test.sh | grep L4
```

## 关联条目

- 原则: R52（证据一致性——自审/门禁结论必须与被检文件真实内容相符）
- 相关: E129（HMDFS umask 077 → 022，本 E546 正是修 E129 那个补丁时暴露的）
