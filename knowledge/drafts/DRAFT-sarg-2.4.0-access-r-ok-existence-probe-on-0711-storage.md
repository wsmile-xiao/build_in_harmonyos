# OHOS `/storage` 以 0711 挂载：上游用 `access(path, R_OK)` 做"目录是否存在"的判据会假阴，进而误发 `mkdir` 并把 `EEXIST` 当致命

## 一句话

OHOS 上 `/storage` 是 `drwx--x--x`（0711）：非属主可以**进入**（x）但不能**读目录项**（r）。
上游若用 `access(prefix, R_OK)` 来判断"这个路径前缀是不是已经存在"，那么在 OHOS 上对一个
**确实存在**的目录也会返回 `-1 / EACCES`。代码于是认定"不存在"，去 `mkdir()`，结果拿到
`EEXIST` —— 而很多老代码把 `EEXIST` 也当致命错误直接 `exit()`，于是构建/运行在一条
"看起来是权限问题、其实是判据选错"的路径上中断。

## 现场（sarg 2.4.0，`util.c` 的 `my_mkdir()`）

上游逐级扫描路径、在每个 `/` 处测试前缀（原始代码，`util.c:441`）：

```c
if (chars>0 && name[i] == '/') {
        w0[i] = '\0';
        if (access(w0, R_OK) != 0) {          /* ← 把 R_OK 当作"存在性"判据 */
                if (PortableMkDir(w0,0755)) { /* 已存在时 → EEXIST */
                        debuga(...  _("Cannot create directory \"%s\": %s\n") ...);
                        exit(EXIT_FAILURE);   /* ← EEXIST 被当致命 */
                }
        }
}
```

在 OHOS 上，`my_mkdir()` 一旦需要创建位于 `/storage/...` 下的多级目录，第一级前缀就会被
`access(..., R_OK)` 判成"不存在"，随后 `PortableMkDir` 报 `EEXIST`，程序 `exit(EXIT_FAILURE)`。

## 修法（最小、只改判据）

```c
if (access(w0, F_OK) != 0) {   /* 前缀只需要"存在"，不需要可读 */
```

即补丁 `0004-util.c.patch`：把存在性判据从 `R_OK` 换成 `F_OK`。
**为什么不去改挂载权限**：那是设备侧不可控、也不该由配方改的东西；而且真正错的是代码用了
错误的模式位，不是文件系统。

## 判据（怎么确认就是这条，而不是别的权限问题）

- 报错形如 `Cannot create directory "...": File exists`（`EEXIST` 而不是 `EACCES`）——
  **矛盾点**：代码刚"测过"这个目录不存在，创建时却说它已存在 ⇒ 说明存在性判据假阴。
- 同一目录用 `ls` / `stat` 看得见 ⇒ 目录确实存在。
- 用最小 C 程序对同一目录分别测 `access(p, R_OK)` 与 `access(p, F_OK)`：前者 `-1/EACCES`、
  后者 `0` ⇒ 直接锁定是模式位选错。
- 挂载点权限可查：`/storage` 为 `drwx--x--x`。

## 适用边界（诚实标注）

- 已在 sarg 2.4.0 的 `util.c:441` 实证（补丁 diff 与代码内注释即证据）。
- **跨包普遍性未验证**：本条只说明"上游用 `R_OK` 当前缀存在性判据"这类写法在 OHOS 上会坏，
  不代表所有包都这样写；遇到 `EEXIST` 类致命错误时值得按上面的判据排查，但不要先验地认定就是它。
- 不适用：HMDFS 上 `umask 077` 建出目录后自己不可写（那是"建得出来但用不了"，
  症状是 `Permission denied` 于后续写入，先例 `archives/a/aide/0.19.3`）；
  也不适用 E303（hostfs 把 `opendir("/")` 的 `EACCES` 当成坏文件名，消费方是目录枚举而非 `mkdir` 前置判据）。

## 查重状态

`draft-review`（2026-09-23 实跑）质量预检三项 ✅；TOP5 = E303 0.02、E524 0.02、E220 0.01、
E076 0.01、E320 0.01，全部低于合并阈值 ⇒ 预审建议 **create**。
