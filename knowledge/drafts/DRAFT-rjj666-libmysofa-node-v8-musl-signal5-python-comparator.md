# DRAFT-rjj666-libmysofa-node-v8-musl-signal5-python-comparator

## 基本信息
- **严重度**: 1
- **类别**: musl | runtime | test | nodejs | substitution
- **作者**: rjj666

## 错误特征
```
node -e "1" → Signal 5 (SIGTRAP)，V8 在 musl 初始化即崩
依赖 node 的测试脚本全部失败，报错与被测库无关
```

## 根因分析
V8 在 OHOS musl 上初始化即触发 Signal 5，node 无法运行任何脚本——
运行时与 libc 深层不兼容，无"修好"选项。libmysofa 的 16 项 JSON
语义比对用例依赖 node，只能替换比对执行器。

## 推荐方案
**方法**: semantic-equivalent-python-comparator（语义等价 python 比对器替换）

**说明**: json_diff_ohos.py 用 python 标准库复刻上游 node 比对脚本的
判定逻辑（忽略键序/格式差异），补丁改写 compare.sh /
compareIgnoreNew.sh 调用它。要点：a) 比对语义逐条对齐，不能变严/变松；
b) 沙箱 deny open(2) symlink，引用 python 须先解析软链为实体路径；
c) 干净 PATH 下验证（垫片劫持裸命令会造成假失败）。

## 验证
```bash
ctest --output-on-failure   # 替换后 43/43 原生全绿（含 16 项比对用例）
```

## 来源
- 草稿: DRAFT-rjj666-libmysofa-node-v8-musl-signal5-python-comparator
- 关联: E292, E356, E400
- 提升日期: 待审核
