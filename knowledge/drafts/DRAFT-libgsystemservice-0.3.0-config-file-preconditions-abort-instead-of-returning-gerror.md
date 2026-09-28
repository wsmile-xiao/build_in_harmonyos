# DRAFT：同一个 API 里「返回 GError」和「直接 abort」混着来 —— 写负向测试前必须先分清

> 状态：草稿（待知识库主编 promote）
> 来源：libgsystemservice 0.3.0 适配，`archives/l/libgsystemservice/0.3.0`
> 类别：api-semantics / error-handling / contract-mismatch / testing

## 一、起因

给 `libgsystemservice` 写消费端测试（`test_package/test.c`）时，要给
`GssConfigFile` 的取值函数配**负向对照**（喂坏输入、断言报错）。顺手想加一条
「key 不存在应该报 `G_KEY_FILE_ERROR_KEY_NOT_FOUND`」——读源码发现：**它不会
报错，它会 abort。**

## 二、`GssConfigFile` 的失败呈现方式，是混着来的

### (a) 构造期：默认配置读不到 → abort，不是返回 NULL

`gss_config_file_new()` 的 docstring 写着：

```
* Create a new #GssConfigFile representing the configuration loaded from the
* given collection of @key_file_paths, ...
*
* This function does no file I/O.
*
* Returns: (transfer full): a newly allocated #GssConfigFile
```

两句话都对，合起来却会误导人。看 `constructed()`：

```c
  /* Chain up. */
  G_OBJECT_CLASS (gss_config_file_parent_class)->constructed (object);

  /* Load the default config file from the given resource. It's a fatal error
   * if this fails. We load this in the constructor to ensure we fail early,
   * rather than conditionally on accessing something from the config file. */
  g_assert (self->default_resource != NULL);
  g_assert (self->default_path != NULL);

  bytes = g_resource_lookup_data (self->default_resource, self->default_path,
                                  G_RESOURCE_LOOKUP_FLAGS_NONE, &error);
  g_assert_no_error (error);                       /* ← default_path 写错 → abort */

  self->default_key_file = g_key_file_new ();
  g_key_file_load_from_bytes (self->default_key_file, bytes,
                              G_KEY_FILE_NONE, &error);
  g_assert_no_error (error);                       /* ← 默认配置语法错 → abort */
```

「no file I/O」说的是 `key_file_paths` 里那些**磁盘文件**是惰性加载的（
`gss_config_file_ensure_loaded()` 里才 `g_key_file_load_from_file()`，而且
`G_FILE_ERROR_NOENT` 被显式忽略）。而 `default_resource` / `default_path`
指的那份默认配置是**构造期就强制读**的，失败即 abort。

> 所以：`gss_config_file_new()` 不是「构造一个空壳，用的时候再加载」，
> 而是「构造期就要把 resource 里那份默认配置读进来」。`default_path` 拼错
> 不是可捕获的错误，是**对象构造即进程终止**。

### (b) 查询期：key 在所有文件里都不存在 → 同样 abort

`gss_config_file_get_file_for_key()` 逐个候选文件查这个 key：

```c
  for (i = 0; i <= self->n_paths; i++)
    {
      path = (i < self->n_paths) ? self->paths[i] : self->default_path;
      if (!gss_config_file_ensure_loaded (self, i, &key_file, error))
        return FALSE;
      if (g_key_file_has_key (key_file, group_name, key_name, NULL))
        break;
    }

  /* Not found? */
  if (i > self->n_paths)
    {
      key_file = NULL;
      path = NULL;
    }
  ...
  return TRUE;                        /* ← 注意：返回 TRUE，只是 key_file 是 NULL */
```

调用方拿到之后：

```c
  if (!gss_config_file_get_file_for_key (self, group_name, key_name, &key_file, NULL, error))
    return 0;
  g_assert (key_file != NULL);        /* ← 走到这里 = abort */
```

`get_uint` / `get_boolean` / `get_string` / `get_strv` 四个函数里各有一条这样的
`g_assert`。文档的措辞是：

> The given key **must exist** in the default configuration file, if not in any others.

这确实是个前置条件——但它违约的代价是**进程终止**，不是
`G_KEY_FILE_ERROR_KEY_NOT_FOUND`。

### (c) 同一批函数里，另外几种失败**是**正常的 GError

这才是最容易判断错的地方：

| 调用 | 失败情形 | 呈现 |
| --- | --- | --- |
| `gss_config_file_new(paths, res, 拼错的 default_path)` | 资源里找不到 | **abort** ⚠️ |
| `get_uint(...)` 值越界 | 不在 `[min, max]` 内 | `G_KEY_FILE_ERROR_INVALID_VALUE` ✅ |
| `get_*()` 某个候选文件语法坏 | 解析失败 | `G_KEY_FILE_ERROR_PARSE` ✅ |
| `get_*()` 该 key 哪儿都没有 | 前置条件违约 | **abort** ⚠️ |
| `get_groups()` | 不带 key 参数，无此 `g_assert` | 只返回组列表 ✅ |

也就是说，**不能按库名或类名一刀切判断「这个 API 报错还是崩」**，只能一个
函数一个函数地读源码：看 `g_assert*` / `g_return_val_if_fail` / `g_error_new`
出现在哪里。

## 三、为什么这在 CI 上特别贵

abort 会**把同一个测试二进制里剩下的用例全部带走**。日志尾部只剩：

```
** ERROR:config-file.c:NN:...: assertion failed (key_file != NULL)
Bail out!
```

看起来像环境坏了或构建坏了，不像「这一条用例本来就不该这么写」。一轮 CI 白烧，
排查方向还会被带偏。

正确姿势：**先分类，再决定断言**。要覆盖 abort 型前置条件，就开**子进程**
（`g_test_trap_subprocess`，GLib 自带；或 `g_spawn_sync` 一个最小程序），
断言子进程的终止方式，而不是在主进程里直接触发。

## 四、落到消费端测试上怎么写

本包 `test_package/test.c` 最终只对 **GError 型**失败做负向对照，两类各一条：

```c
/* 反向对照一：越界必须被拒绝，而不是 clamp */
CHECK (gss_config_file_get_uint (config, "Test", "Number", 5000, 6000, &error) == 0);
CHECK (g_error_matches (error, G_KEY_FILE_ERROR, G_KEY_FILE_ERROR_INVALID_VALUE));
g_clear_error (&error);

/* 反向对照二：候选文件语法坏必须报 PARSE，而不是被当成「没有这个 key」 */
CHECK (gss_config_file_get_uint (broken_config, "Test", "Number", 0, G_MAXUINT, &error) == 0);
CHECK (g_error_matches (error, G_KEY_FILE_ERROR, G_KEY_FILE_ERROR_PARSE));
g_clear_error (&error);
```

两条都是**返回值 + error 一起断言**：`get_uint` 失败时返回 `0`，如果只断言
返回值就会把「读失败」误读成「值是 0」。

## 验证命令

```bash
# 1) 文档说的和实现做的是不是一回事 —— 先读 constructed()
grep -n 'g_assert_no_error\|g_assert (' <src>/libgsystemservice/config-file.c
#   → 构造期两条 g_assert_no_error + 四个 get_* 各一条 g_assert (key_file != NULL)

# 2) 「找不到 key」这条路径的真实返回值
sed -n '/Not found?/,/return TRUE/p' <src>/libgsystemservice/config-file.c
#   → key_file = NULL; 然后 return TRUE    ← 违约发生在调用方

# 3) 想覆盖 abort 型前置条件？用子进程，别在主进程里试
grep -n 'g_test_trap_subprocess' -A 12 <src>/libgsystemservice/tests/config-file.c
```

## 禁止策略

| 禁止 | 原因 | 后果 |
| --- | --- | --- |
| 断言「缺 key 返回 GError」 | key 哪儿都没有时返回的仍是 TRUE，违约在调用方的 `g_assert (key_file != NULL)` | 测试二进制当场终止，其后用例全部未执行；日志只剩 `Bail out!`，被误判为环境故障 |
| 按 docstring 推断错误行为 | docstring 只声明前置条件，不声明违约代价（abort 还是 GError） | 断言写错，而且错得看不出来 |
| `get_uint` 只断言返回值不断言 error | 越界/失败时返回 0 且带错误 | 把「读失败」当成「值是 0」——静默假通过 |
| 在主进程里触发 abort 型前置条件做「负向用例」 | abort 会杀掉同二进制内其余所有用例 | 用一条用例写错，换来整套覆盖归零 |

## 关联

- `similar_to` **DRAFT-clips-6.3-embedded-api-semantics**：同属「按 API 语义的
  字面意思推断行为」这一类错误。
- `similar_to` **E265**：上游测试的注册表与执行集不是一回事——同样是「契约的
  字面表述与真实行为不一致」。
- `archives/l/libgsystemservice/0.3.0/test_package/test.c`：本条规则的落地样本
  （负向对照只挑 GError 型的两种失败）。
