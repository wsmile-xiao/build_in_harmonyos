# DRAFT: OHOS app 数据分区对未签名脚本 chmod 755 后仍拒绝执行——"复制到非 HMDFS"不是万能解

- Status: UNMATCHED
- Category: platform / security / permissions
- Keywords: Permission denied, exec, chmod 755, /data/storage/el2/base/haps/entry/files, HMDFS, 未签名脚本, shebang, ELF 签名, E087, E054
- Related: E087, E054, E077

## 现象（trickle-1.08 真机 r7 实测，2026-10-01）

conan automake 包的 `bin/aclocal`（sh wrapper）在 HMDFS 上执行报
`Permission denied`。按既有经验"复制到非 HMDFS 分区"处理：

```sh
cp -r <conan automake pkg> /data/storage/el2/base/haps/entry/files/tt/
chmod -R 755 /data/storage/el2/base/haps/entry/files/tt/
ls -l .../tt/bin/aclocal   # -rwxr-xr-x 1 currentUser ...  ← 权限位正确、属主正确
.../tt/bin/aclocal --version   # 仍然 Permission denied ！
```

**权限位已是 `rwxr-xr-x` 且属主即当前用户，直接 exec 仍被拒**。同分区
内任意自建 sh 脚本同样如此。

## 根因

执行限制不止"HMDFS 无执行位"一层：`/data/storage/el2/base/haps/entry/files/`
（app 数据分区）对**未经代码签名的新文件**（脚本与未签名 ELF）同样
拒绝 exec——chmod 修的是 mode 位，绕不过签名/SELinux 域校验。该分区
对已用 `binary-sign-tool` 签名的 ELF 才是可执行安全区。

## 方案

对**脚本**类产物，正确解法不是找分区，而是**显式解释器调用**：

```sh
sh  <script.sh>          # sh 脚本：读取无限制
perl <script.pl> <args>  # perl 脚本（如 conan automake 包的 .aclocal-real）
```

只有解释器本身（/data/service/hnp/bin/{sh,perl,bash}，系统已签名）需要
可执行。对**ELF** 产物仍走签名（binary-sign-tool -selfSign）或保持在该
分区由 CI 的签名流程处理。

## 验证

- chmod 755 后直接 exec：`Permission denied`（复现两次）。
- 同一文件 `sh <file>` / `/data/service/hnp/bin/perl <file>`：正常执行；
  trickle 配方据此实现解释器自举回退并在真机全链验证通过（r23 全绿）。

## 复用面

任何"把构建工具/测试脚本复制到非 HMDFS 分区 + chmod"的方案都应先做
此区分：脚本能用解释器直跑就别折腾分区；只有签名过的 ELF 才依赖该
分区。避免在"换分区 + chmod"上浪费整轮真机（本条即由一轮真机换取）。
