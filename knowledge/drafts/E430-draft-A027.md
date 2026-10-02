# E430 — 共享 conan 缓存陈旧 .so 污染（运行行为偏离源码）

## 错误特征
运行实测值与源码公式不符（如 easing 端点值与源码公式手工推导/独立实现
计算结果对不上）；源码 md5/反汇编与当前源码一致但运行行为不符；崩溃点
随 .so 新旧而漂移（换新构建后异常消失或变化）。

## 触发条件
- 构建系统: conan 缓存（任意包）
- 阶段: run/test（同机多任务并行 / 多会话共享 ~/.conan2 的环境）

## 根因分析
旧会话（不同 recipe revision / 不同源码）残留同包的 build/package 目录，
conan 目录名哈希碰撞使陈旧目录被复用——运行加载的是陈旧 .so。conan 不会
对已存在的 source 目录重新校验 sha256（只在下发下载时刻校验），陈旧
source/build 包目录可长期潜伏。实测：09-14 会话残留 libadwaita/1.8.8
缓存导致 easing 实测值偏离源码公式、SIGSEGV 崩溃点漂移；
`conan remove "libadwaita/*" -c` 全清 + clean-room 重建后行为与源码一致。

## 解决方案

### 推荐方案
`conan remove "<name>/*" -c` 清本包全部旧条目后 clean-room 重建；
核验包目录 .so 的 mtime/sha256。多任务并行机器上正式构建前必清本包
旧条目。

### 禁止做法
- ❌ 依据"运行值与源码不符"直接改源码（偏差在缓存不在源码）
- ❌ 信任 conan 缓存中 .so 的新鲜度（mtime/sha256 核验是硬要求）
- ❌ 在共享缓存环境跳过清缓存直接正式构建

## 验证
```bash
conan remove "libadwaita/*" -c
conan create archives/l/libadwaita/1.8.8/conanfile.py --build=missing
# 重建后运行值与源码公式一致
```

## 关联条目
- 相关: E429（同一次排查中发现——陈旧 .so 使类型混淆崩溃点漂移）
