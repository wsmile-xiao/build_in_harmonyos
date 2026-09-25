# E543（草稿）refresh-patch 生成空补丁：.work 与 .orig 是硬链接

## 现象

改完源码跑 `refresh-patch --auto`，工具明明识别到文件变更，却产出空结果：

```
ℹ️   追踪到 1 个文件变更:
ℹ️     ✏️ Makefile
ℹ️   精准模式: 只对 1 个追踪文件生成补丁（无需排除规则）
ℹ️   无有效新补丁，保留现有
```

`patches/` 为空，`conandata.yml` 里 `patches: {}` 原封不动。此时本地 `.work` 目录里
改动"看着"好好的，容易误以为工具抽风。

## 根因

`init-build` 建工作副本时用的是**硬链接**（日志里就写着 `.work 已创建 (硬链接)`）：

```
$ ls -li since-1.1.orig/Makefile since-1.1.work/Makefile
11563894 -rw-r--r-- 2 root root 655 ... since-1.1.orig/Makefile
11563894 -rw-r--r-- 2 root root 655 ... since-1.1.work/Makefile
         ↑ 同一 inode，链接数 2
```

只要修改工具是"**原地写回**"（以 `O_TRUNC` 打开原文件写入），两个路径指向的是同一份
数据，`.orig` 会被一起改掉。`refresh-patch` 的 per-file difflib 比对 `.orig` 与 `.work`，
结果自然是零差异 → "无有效新补丁"。

反之，`sed -i` 和多数编辑器采用"写临时文件再 rename"，rename 会让 `.work` 指向新 inode，
硬链接自动断开，因此这类工具不触发本问题——这也是它长期没被发现的原因。

危害不止于"补丁没生成"：配方会在干净源码上构建，**所有适配改动都不存在**，而本地
`.work` 里改动还在，`make` 手工验证也是通过的，形成"本地对、发布错"的假象。

## 确认

```bash
ls -li "$BUILD_SRC_DIR/Makefile" "${BUILD_SRC_DIR%.work}.orig/Makefile"
# 两行 inode 相同 → 命中
diff -u "${BUILD_SRC_DIR%.work}.orig/Makefile" "$BUILD_SRC_DIR/Makefile"
# 无输出，但文件内容确实已改 → 确认
```

## 修复

```bash
O=/root/tmp/builds/since-1.1.orig
W=/root/tmp/builds/since-1.1.work

cp "$W/Makefile" /tmp/Makefile.mod                       # 1. 备份改好的文件
rm -f "$O/Makefile" "$W/Makefile"                        # 2. 断开硬链接
tar xzf since-upstream-1.1.tar.gz -O --wildcards '*/Makefile' > "$O/Makefile"
sha256sum "$O/Makefile"                                  #    核对与上游一致
cp /tmp/Makefile.mod "$W/Makefile"                       # 3. 放回修改版

ls -li "$O/Makefile" "$W/Makefile"                       # inode 必须不同
python3 scripts/ohc-run.py refresh-patch --auto since 1.1
# ✅ 0001-Makefile.patch (+6/-5)
```

预防：动手改源码之前，先确保目标文件在 `.work` 里独占 inode
（`cp --remove-destination` 或 `rm` 后重建），或者只用会 rename 的编辑方式。

## 不要这样做

- 不要手写 `.patch` 绕过（R3）：手写补丁的行号/上下文与真实源码容易漂移，
  `conan create` 阶段 `patch_ng` 报 `source/target file does not exist`，
  或补丁静默不生效——CI 构建的其实是未打补丁的源码。
- 不要直接在 `conandata.yml` 里声明一个还没生成的补丁文件。

## 与 E484 的区别

E484 讲的是 HarmonyOS 上 `patch --dry-run` 会真的创建 0 字节占位文件，污染的是
**新增文件**的补丁头（`--- a/x` vs `--- /dev/null`）；本条根因是 `.orig` 与 `.work`
共享 inode，污染的是**基线内容本身**，两者触发路径和修复手法都不同。

## 实测来源

since 1.1 适配（`archives/s/since/1.1`）：修改上游 Makefile 使其尊重外部
`CC/CFLAGS/CPPFLAGS/LDFLAGS` 后首次 `refresh-patch --auto` 空转，按上述方法还原
`.orig` 后一次生成成功。
