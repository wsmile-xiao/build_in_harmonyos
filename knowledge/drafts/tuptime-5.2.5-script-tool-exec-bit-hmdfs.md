# 解释型脚本工具打包：可执行位 + HMDFS 上的 PATH/X_OK 陷阱

> Draft: `DRAFT-TUPTIME-525-SCRIPT-TOOL-EXEC-BIT-HMDFS`
> Stem: `tuptime-5.2.5-script-tool-exec-bit-hmdfs` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-TUPTIME-525-SCRIPT-TOOL-EXEC-BIT-HMDFS
- **严重度**: 2
- **类别**: packaging|testing|platform
- **触发工具**: conan|manual
- **阶段**: packaging

## 现象（tuptime 5.2.5 实测，两个坑连续踩中）

**坑 A —— 装出来的 bin/ 没有可执行位：**

```console
$ ls -l <pkg>/bin/tuptime
-rw-rw---- 1 user user 47628 ... tuptime          # ← 0660，不可执行
$ python3 -c "import os;p='<pkg>/bin/tuptime';print(oct(os.stat(p).st_mode), os.access(p,os.X_OK))"
0o100660 False
```

**坑 B —— 加了 chmod 之后，PATH 解析仍然找不到：**

```console
$ chmod 755 <pkg>/bin/tuptime && ls -l <pkg>/bin/tuptime
-rwxrwx--- 1 user user 47628 ... tuptime           # 实际可执行
$ python3 -c "import shutil;print(shutil.which('tuptime', path='<pkg>/bin'))"
None                                               # ← X_OK 探测假阴性（HMDFS）
```

结果 `conan create` 的 test_package 报：

```
FAIL: 'tuptime' not found in PATH — package bin/ not on PATH
ConanException: Error 2 while executing
```

尽管 `VirtualRunEnv` 生成的 `conanrunenv-*.sh` 明明写着
`export PATH="<pkg>/bin:$PATH"`。

## 根因

1. **权限继承**：脚本工具没有编译阶段，"安装"就是 `copy()`；`copy()` 保留源文件权限。
   上游 release tarball 里的 `src/tuptime` 是 **0664**，发行版安装器靠
   `install -m 755`（`tuptime-install.sh:121`）或 postinst 补权限。conan 侧不补 →
   交付物不可执行。
2. **HMDFS 权限语义**：本平台 chmod 结果不可靠/被归一化（参 E046），
   `os.access(X_OK)` 常返回 False，`shutil.which()` 因此把正常文件判成缺失。

## 推荐方案

**方法**: `chmod-in-package-and-resolve-bindir-absolutely`

1. `package()` 里显式 `os.chmod(os.path.join(self.package_folder, "bin", "<tool>"), 0o755)`
   —— 可执行位是交付物的一部分。
2. `test_package` **不要**用 PATH / `shutil.which` 解析被测产物：

   ```python
   bindirs = list(self.dependencies[self.tested_reference_str]
                  .cpp_info.aggregated_components().bindirs)
   tuptime = os.path.join(bindirs[0], "tuptime")
   self.run(f'"{sys.executable}" "{script}" "{tuptime}"', env="conanrun")
   ```

   断言脚本里 PATH 查找只作 fallback。
3. 用**显式解释器**启动脚本（`sys.executable` + 脚本绝对路径），别依赖 PATH 里的 `python3`。
4. 判断"存在/可执行"用 `os.path.isfile()`（必要时读 `st_mode`），**不要**用
   `os.access(X_OK)`（HMDFS 假阴性）。
5. 断言仍要真实执行被测物（R34）。

## 验证命令

```bash
ls -l <pkg>/bin/<tool>
python3 -c "import os;p='<pkg>/bin/<tool>';print(oct(os.stat(p).st_mode), os.access(p,os.X_OK))"
<pkg>/bin/<tool> -v; echo "exit=$?"
```

## 取证记录

- 包: tuptime 5.2.5（`archives/t/tuptime/5.2.5`）
- 逐字证据: `reports/conan-create.log`（首次 test_package 失败与修复后 11/11 通过）
