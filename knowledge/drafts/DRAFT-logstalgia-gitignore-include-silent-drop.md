# E543 草稿：gitignore `archives/**/include/` 静默吞配方头文件——本地假绿、CI 必红

## 错误特征
```
fatal error: 'GL/glew.h' file not found
（本地 conan create 双 profile 干净重建全绿；CI checkout 后同配方必红）
```

## 根因
仓库 .gitignore 的 `archives/**/include/`（拦编译产物）同样匹配**配方源码树**
的 include/ 子目录。git add 目录级操作不告警，文件从未进 commit：
- 本地构建读工作区磁盘 → 文件在 → 绿
- CI 只 checkout commit → 文件缺 → 红

## 解法
1. `git check-ignore -v <file>` / `git ls-tree -r HEAD | grep <pkg>` 一条命令定性
2. 头文件挪出 include/ 路径（compat/include/GL/x.h → compat/GL/x.h，-I 指向 compat/）
3. build() 加 _materialize_compat 式防御回拷（recipe_folder → source_folder）
4. **红线**：本地等价 CI 的验证必须 `git clone --depth 1 --branch <b>` 干净源构建

## 验证
PR #9149：#42950 红（文件缺失）→ 迁移后 #42989/#42999 绿 + 本地干净 clone 全绿。

## 关联
- E467（conftest 依赖闭包加载）：同为"本地/CI 环境差异"类，但根因在 git 层非 loader 层
