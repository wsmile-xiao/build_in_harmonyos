# E429 — HMDFS 大小写不敏感：仅大小写不同的改名被误判 conflict，且 rename(2) 为 no-op

## 错误特征

在鸿蒙 PC 用户存储（`/storage/Users/currentUser`，HMDFS）上：

```
$ bash slugify -v README.md Photo.JPG
conflict: README.md
conflict: Photo.JPG
$ mv README.md readme.md
mv: 'README.md' and 'readme.md' are the same file
```

改名工具不报错退出（rc=0），但名字没有变；大小写敏感的 Linux 构建机上同样的命令完全正常。

## 触发条件
- 构建系统: 无（运行期行为，脚本/CLI 工具）
- 阶段: runtime / test_package（测试目录落在大小写不敏感存储上时）
- 文件系统大小写不敏感（HMDFS；本地可用 vfat 回环挂载复现）
- 工具做「仅大小写不同」的改名（小写化、slug 化），并在改名前检查目标是否已存在

## 根因分析

1. 大小写不敏感 FS 上 `readme.md` 解析到 `README.md` 这个目录项，`[ -e readme.md ]` 恒为真。
   slugify 1.0.1 用它防覆盖，只对 `$OSTYPE=darwin*` 特判；鸿蒙 bash/5.3 的 `OSTYPE` 是 `linux-gnu`，
   于是所有仅大小写不同的改名都被判为 conflict。
2. 跳过检查也不行：新旧名指向同一 inode 时，内核 `rename(2)` 按 POSIX 直接返回成功、不改目录项；
   GNU `mv` 先判 same file 并拒绝。vfat 实测：`mv` rc=1，`os.rename` 成功但名字仍是 `README.md`。
3. 大小写语义取决于挂载点（`/storage` 用户存储为 HMDFS），按平台名（OSTYPE/uname）判断不可靠。

## 解决方案

### 推荐方案
按文件身份识别别名，经临时名两步改名（`archives/s/slugify/1.0.1/patches/0001-slugify.patch`）：

```bash
case_alias=0
if [ "$source" -ef "$target" ]; then case_alias=1; fi       # 同一 inode = 大小写别名
...
if [ $case_alias -eq 1 ]; then
  tmp_name="${source%/}.slugify.$$"                          # 去尾斜杠，兼容 Tab 补全的目录参数
  if [ -e "$tmp_name" -o -L "$tmp_name" ]; then echo "conflict: $source"; continue; fi   # 临时名被占用不覆盖
  mv "$source" "$tmp_name" || continue
  if [ -e "$target" -o -L "$target" ]; then                  # 独立的硬链接/符号链接：还原并报冲突
    mv "$tmp_name" "$source"; echo "conflict: $source"; continue
  fi
  mv "$tmp_name" "$target" || { mv "$tmp_name" "$source"; continue; }     # 第二步失败改回源名
fi
```

- 真冲突（目标是另一个文件）仍然 `conflict`，不覆盖；
- 大小写敏感 FS 上结果与上游一致（唯一差异：dry-run 对「目标恰为源的硬链接」预演为 rename，实跑仍报 conflict）。

### 回退方案
逐目录探针（`touch CaseProbe; [ -e caseprobe ]`）判定大小写敏感性，不敏感时对「转小写后相同」的目标走两步改名。
缺点是 dry-run 也要写文件、目录必须可写。

### 禁止做法
- ❌ 按 `$OSTYPE`/`uname` 把整个平台判为大小写不敏感并关闭冲突检查（上游 darwin 分支的做法）——真冲突时 `mv` 静默覆盖另一个文件
- ❌ 仅大小写不同时直接 `mv "$source" "$target"` 且不核对结果——rename 是 no-op，名字不变

## 验证
```bash
# 本地复现大小写不敏感 FS（需 root）
truncate -s 16M vfat.img && mkfs.vfat vfat.img && mount -o loop vfat.img mnt
cd mnt && touch CaseProbe && ls caseprobe                  # 命中 = 大小写不敏感
touch README.md && bash slugify -v README.md && ls         # 上游: conflict；补丁后: rename，列表为 readme.md
# 消费者用例（在该挂载点上跑）
SLUGIFY_TEST_ROOT=$PWD bash test_package/test_slugify_ohos.sh <pkg>/bin/slugify
```

实测（OHOS bash/5.3 经 qemu，vfat）：补丁版鸿蒙特有用例 5/5；未打补丁的上游 1/5（HC-1/2/3/5 均报 conflict）。

## 关联条目
- 同源平台属性: E193（HMDFS 大小写不敏感导致测试失败）
- 相似: E416（大小写不敏感 FS 双 case 目录）、DRAFT-inform6-compiler-6.42-case-insensitive-alias-samefile（package() 别名副本 SameFileError）、E999-draft-35E4（归档目录大小写两步改名）
- 原则: P013（平台限制降级而非绕过）、P016（HMDFS 限制用替代方案）
