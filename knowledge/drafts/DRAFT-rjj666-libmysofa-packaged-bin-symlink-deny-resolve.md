# DRAFT-rjj666-libmysofa-packaged-bin-symlink-deny-resolve

## 基本信息
- **严重度**: 2
- **类别**: sandbox | symlink | ohos | test | packaging
- **作者**: rjj666

## 错误特征
```
实体文件可执行，经软链路径 exec 报 Permission denied (EACCES)；
同一软链在 shell/python 域 readlink、读内容均正常——域不对称
```

## 根因分析
OHOS 沙箱对打包产物 open(2) 一个 symlink 组件直接 EACCES，即使
实体文件可执行。脚本 shebang 或脚本内对解释器的软链引用由此
假性失败，且"shell 域复核正常"极易误导排查方向。

## 推荐方案
**方法**: resolve-realpath-before-exec（调用前解析实体路径）

**说明**: 脚本内先 os.path.realpath / readlink -f 解析为实体文件再 exec；
shebang 场景由外层 wrapper 以"实体解释器 脚本"形式调用。
Linux CI 上软链直调本就合法，解析实体路径无副作用，补丁双向通用。

## 验证
```bash
readlink -f <interpreter>   # 解析实体路径
ctest --output-on-failure    # 43/43 全绿
```

## 来源
- 草稿: DRAFT-rjj666-libmysofa-packaged-bin-symlink-deny-resolve
- 关联: E001, E018, E037, E095
- 提升日期: 待审核
