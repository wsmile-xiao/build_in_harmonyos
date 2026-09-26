# DRAFT-ohos-hmdfs-packaging-install-sh-eprem：HMDFS 上 make install 的两类必失败与 copy() 显式打包

> Status: Draft | Updated: 2026-09-13
> Source: dinotrace 9.4f HarmonyOS PC 适配（打包阶段实测复现）
> 对应：knowledge/drafts/DRAFT-ohos-hmdfs-packaging-install-sh-eprem.kv
> 关键词：HMDFS, make install, install-sh, cp EPERM, Error 126, DESTDIR, package()

## 现象或适配场景

autotools 包编译成功，却卡在打包/安装阶段，且报错点与源码无关：

```text
# 失败 1：上游把刚构建的二进制 cp 到顶层目录
(cp obj_dir/dinotrace ./dinotrace >/dev/null 2>&1 || cp obj_dir/dinotrace.exe ...)
cp: /storage/.../b/dinotrace: Operation not permitted
make: *** [Makefile:135: dinotrace_exe] Error 1

# 失败 2：上游用随包的 install-sh 安装 info 文件
for i in *.info*; do ./install-sh -c -m 644 $i <DESTDIR>/share/info/$i; done
/bin/sh: ./install-sh: can't execute: Permission denied
make: *** [Makefile:196: install-info] Error 126
```

## 根因

OHOS 的 **HMDFS 对权限做归一化**：

1. 对**已存在**的可执行文件做原地覆盖写（`cp` 会截断重写目标）被判 EPERM——目标正是上一次
   `make` 刚产出的同名二进制；实测 `rm -f` 之后同一个 `cp` 立即成功（说明与路径/属主无关，
   只与"目标已存在"有关）。
2. 从 tar 解出的辅助脚本（`install-sh`、`mkinstalldirs` 等）虽然 `ls -l` 显示可执行，
   但内核 `execve` 仍拒绝（chmod 位不生效），只能 `sh <script>` 调用或绕开。

因此任何**依赖"先 make 再 cp 覆盖"或"exec 随包脚本"**的上游安装路径，在 HMDFS 上必然失败；
如果 `package()` 里用 `ignore_errors=True` 吞掉，就会出现"包看起来构建成功、产物其实缺失"的
静默半成品。

## 修复步骤

1. `package()` 改用 conan `copy()` 显式安装真实产物（`bin/<exe>`、`share/info/*.info`、
   `licenses/COPYING`），并**镜像上游 install 规则的目标路径**；
2. 安装后对每个必需产物做 `os.path.isfile` 断言，缺失即 `raise ConanException`（防止静默半成品）；
3. 若想保留上游 `make install` 的日志留证：先 `rm -f` 顶层同名二进制、把 `DESTDIR` 指向
   `build_folder` 下的 staging 目录（**不落 package_folder**）、并保持 `ignore_errors=True`——
   绝不让它成为产物来源。

```python
copy(self, "dinotrace", src=self.build_folder,
     dst=os.path.join(self.package_folder, "bin"), keep_path=False)
copy(self, "dinotrace.info", src=self.source_folder,
     dst=os.path.join(self.package_folder, "share", "info"), keep_path=False)
staging = os.path.join(self.build_folder, "install-staging")
self.run(f"rm -f dinotrace dinotrace.exe && make install DESTDIR={shlex.quote(staging)}",
         ignore_errors=True, env="conanbuild")
missing = [rel for rel, p in expected.items() if not os.path.isfile(p)]
if missing:
    raise ConanException("packaging incomplete; missing: " + ", ".join(missing))
```

## 验证方式

- 两类失败原始行已实测复现（见上）。
- 修法验证：`conan create` `EXIT_CODE=0`；产物 `bin/dinotrace`（346560 B）、
  `share/info/dinotrace.info`（118559 B）、`licenses/COPYING` 齐全；
  `test_package assertions=6 failures=0`。

## 适用范围和安全边界

适用于所有在 HMDFS 上跑 `make install`/`make DESTDIR=... install` 的 autotools 包（CI worker
与本地 OHOS 设备同限）。边界：**不得**用 `ignore_errors=True` 掩盖安装失败后继续打包——
必须补产物断言；也不要把 staging 写到 `package_folder`，否则半成品会流入制品仓。
