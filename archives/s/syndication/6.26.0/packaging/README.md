# packaging 说明

syndication/6.26.0 为纯库包（libKF6Syndication.so），通过 `conan create` 产出
标准 Conan 包（package 布局：lib/ + include/ + lib/cmake/KF6Syndication/），
发布走制品仓 conan upload 流水线（PR 合并 main 后 CI 自动执行），不单独打
tar.gz 交付包。

- 构建产物：lib/libKF6Syndication.so（+ so.6 / so.6.26.0 版本链）
- 消费方式：`conan install --requires=syndication/6.26.0` 或
  `find_package(KF6Syndication 6.18.0 REQUIRED)`
- 本地缓存包：syndication/6.26.0（conan create 实测 RC=0）
