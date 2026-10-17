# E585 — conandata.yml 数字型版本键未加引号，YAML 解析成 float/int，按 self.version 查 sources 抛 KeyError

## 错误特征

```
conanfile.py (usleep/20160311.094456): Calling source() in .../src
ERROR: conanfile.py (usleep/20160311.094456): Error in source() method, line 46
	get(self, **self.conan_data["sources"][self.version], strip_root=True)
	KeyError: '20160311.094456'
```

`patches` 也按版本作键时，另一种表现更隐蔽：`apply_conandata_patches` 执行
`patches.get(str(self.version), [])` 拿到默认空列表，**不打印任何日志**、一个补丁都不打，
编译可能照常通过（conan 2.29.1 `conan/tools/files/patches.py`，`export_conandata_patches` 同理）。

## 触发条件

- 版本号只含数字且至多一个点：日期版本 `20260609`、`20240116.1`，快照版本 `20160311.094456`，
  两段版本 `2.5`、`3.0`、`1.10`。
- `conandata.yml` 的 `sources`（或 `patches`）用版本作键，且键没加引号：

  ```yaml
  sources:
    20160311.094456:          # ← 裸键
      url: "https://..."
  ```

- 配方按主流写法查找：`get(self, **self.conan_data["sources"][self.version], strip_root=True)`。
- 阶段：`conan source` / `conan create` 的 source()（W3 与 CI 都会失败）。

## 根因分析

Conan 用 `yaml.safe_load`（YAML 1.1 规则）读取 `conandata.yml`。裸键只要符合整数或浮点语法就会被转换：

| 裸键 | 解析结果 | 查 `"<版本>"` |
|------|----------|--------------|
| `20260609` | int `20260609` | KeyError |
| `20240116.1` | float `20240116.1` | KeyError |
| `20160311.094456` | float `20160311.094456` | KeyError |
| `2.5` / `3.0` | float `2.5` / `3.0` | KeyError |
| `1.10` | float `1.1`（尾零丢失） | KeyError |
| `1.2.3` | str `'1.2.3'` | 正常 |
| `"3.0"` | str `'3.0'` | 正常 |

`self.version` 永远是字符串，字典里却是数字键，于是抛 `KeyError`。三段版本号不是合法数字，
所以大多数包从来不会遇到，这也是问题容易被忽视的原因。

`conan-init` 生成的是扁平 `sources`（`url`/`sha256` 直接挂在 `sources` 下），本身不会触发；
按仓库主流写法手工改成版本键时忘了加引号就会中招。

## 解决方案

### 推荐方案

版本键一律加双引号（仓库 945 份 `conandata.yml` 都这么写）：

```yaml
sources:
  "20160311.094456":
    url: "https://github.com/cpeuvrel/usleep-aur/archive/4f880a7a4cd4e0064f10ddc84dda1716c0b99803.tar.gz"
    sha256: "86d1c4f76d99a888497f7148f9acc2637c8016e826f399fb2eeb4179e5ed1a67"
```

### 回退方案

单版本配方可以不用版本键：扁平 `sources` + `get(self, **self.conan_data["sources"], strip_root=True)`，
`patches` 用 list 格式。

### 禁止做法

- ❌ 在配方里把 `self.version` 转成 `float`/`int`，或遍历键做 `str(k) == self.version` 比较来迁就类型推断：
  `1.10` 会变成 `1.1`、前导零会丢，结果不可靠，还掩盖了数据问题。
- ❌ 版本键写成裸数字（`^\s+[0-9]+(\.[0-9]+)?:\s*$`）。

## 验证

```bash
# 所有键都应是 str
python3 -c 'import yaml;print({k:type(k).__name__ for k in yaml.safe_load(open("conandata.yml"))["sources"]})'
# 复现（usleep 20160311.094456 配方去掉引号后）
conan source .   # → KeyError: '20160311.094456'；恢复引号后 conan create 通过
```

## 查重证据

- `engine` 对上述 KeyError 日志误匹配到 E281（资源包 file-copy），与本问题无关。
- E392 覆盖 raw Makefile 配方的 `BadZipFile` / `compiler_executables` KeyError，不涉及 conandata 版本键。
- `DRAFT-shoco-master-conandata-patches-list` 讲的是 patches 用**文件名**作键，不是数字版本键被类型推断。
- 知识库中无 `conandata` + `float`/`int` 版本键的条目或草稿。

## 关联条目

- 相似: E392（raw Makefile 配方的 Conan 通用陷阱）
