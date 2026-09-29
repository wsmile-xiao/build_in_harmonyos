# DRAFT-installkernel-ohos-tmp-readonly

## 鸿蒙 PC 真机 /tmp 只读：探针临时文件必须写权限实测选取

### 现象

真机（HarmonyOS PC）`conan-verify installkernel 4.1` G2 中消费者探针行为
烟测组 3 项断言全挂（sh -n 零告警 / 0 参数干跑 exit 1 / 干跑输出含 Usage），
其余 4 组全过：

```
== [4/5] 行为烟测（sh -n + 0 参数干跑）==
  [FAIL]   sh -n 语法零告警
  [FAIL]   0 参数干跑 exit 1
  [FAIL]   干跑输出含 Usage 行
```

### 根因

- 鸿蒙真机根文件系统只读：`ls -ld /tmp` 为 root 属主、
  `mkdir /tmp/ik-test` 报 **"Read-only file system"**
- 探针把 sh 干跑的退出码/输出重定向到 `/tmp/installkernel-probe/`：
  目录创建失败 → 重定向失败 → rc/out 文件为空 → 断言读不到内容全挂
- 脚本本体与 sh 环境完全正常（手动验证：`sh -n` 退出码 0、干跑打印
  Usage）——Linux CI 上 /tmp 正常，只在真机暴露

### 推荐方案

探针临时目录不硬编码 /tmp，做写权限实测选取：

```cpp
static std::string pick_temp_dir() {
    for (auto e : {"TMPDIR", "TMP", "TEMP"}) {          // 环境变量候选
        const char* v = std::getenv(e);
        if (!v || !*v) continue;
        // 写权限实测：创建子目录→删除，成功即用
        ...
    }
    return ".";                                          // 全不可写回落 cwd
}
```

- 测试期 cwd（构建目录）必然可写，作为最终兜底
- 子目录名带时间戳，避免多会话并发碰撞（真机为共享 shell 环境）
- 本包改后真机八门禁（G0-G4/L2/L4/L5）全绿

### 实证记录

- 2026-09-26 真机：`/tmp` 只读实证 → 探针 pick_temp_dir() 修复 →
  行为烟测真机实跑全过（非 SKIP）
