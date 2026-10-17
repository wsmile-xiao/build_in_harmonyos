# DRAFT-trojan-1.16.0: 已发布 openssl 制品内嵌构建期 OPENSSLDIR，消费方调用打包版 openssl CLI 时默认配置缺失

## 基本信息
- **严重度**: 2
- **类别**: openssl, conan, packaging, relocatability, testing
- **作者**: QOD-BE7
- **来源 PR**: (本 PR)
- **来源 commit**: (待提交后回填)

## 错误特征
```
Can't open "/storage/Users/currentUser/.cache/conan2/p/b/opensf4d50a3c869ab/p/ssl/openssl.cnf" for reading, No such file or directory
error:80000002:system library:BIO_new_file:No such file or directory:crypto/bio/bss_file.c:67:calling fopen(...)
error:10000080:BIO routines:BIO_new_file:no such file:crypto/bio/bss_file.c:75:
ERROR: trojan/1.16.0@ohpcd/stable (test package): Error in test() method, line 25
```

关键指纹：**同一条 `openssl req`，在 `build()` 里的上游冒烟脚本中跑通，在 `test_package` 里跑挂**；
失败点在测试脚本调用 openssl 的那一行，被测库本身已编译、链接、打包完成。

## 根因分析
openssl 在 `Configure` 阶段把 `--openssldir` 解析为一个**编译期写死进二进制的绝对路径**
（`OPENSSLDIR` 常量），因此制品**不可迁移**。ohpcd 已发布的 openssl 二进制是在某个
`CONAN_HOME` 下构建并上传的，实测其内嵌值为
`/storage/Users/currentUser/.cache/conan2/p/b/opensf4d50a3c869ab/p/ssl`；消费方无论从远端缓存拉包、
还是把 `CONAN_HOME` 换到别处（本例 `~/tmp/ch/home-DS16`，包实际落在
`.../home-DS16/p/opens8df551124b5bd/p`），拿到的都是同一份内嵌路径。该路径在本机不存在，
且包目录内也不附带 `openssl.cnf`（`find` 实测无该文件），于是任何**未显式给 `-config`**、
依赖默认配置的子命令（典型是 `openssl req -x509` 自助签测试证书）在读取默认 cnf 时即失败。

`build()` 里之所以正常：那里走 `VirtualBuildEnv`，PATH 命中的是设备自带 openssl
（`~/.harmonybrew/bin/openssl`，其 `OPENSSLDIR` 真实存在）；`test()` 走 `env="conanrun"`，
PATH 被换成包内那份二进制。**判症必须先区分 PATH 命中的是哪一个同名 openssl**，否则会误判为
配方或上游问题。

## 推荐方案
**方法**: `seed-openssl-conf-for-packaged-cli`

**说明**: 在调用打包版 openssl 的消费者脚本顶部显式 `export OPENSSL_CONF=/dev/null`，并把所需字段
全部由命令行显式给出（`-subj`/`-batch`/`-addext`），不再依赖包内或设备默认配置。

**验证/命令**:
```
# 1) 看清 PATH 命中的是哪份 openssl、以及它内嵌的 OPENSSLDIR
cd <test_package> && . ./conanrun.sh
command -v openssl
openssl version -d          # → OPENSSLDIR: "<构建期 conan 包目录>/ssl"
[ -e "<该目录>/openssl.cnf" ] && echo EXISTS || echo MISSING   # 实测 MISSING

# 2) 复现（退出码 1）
openssl req -x509 -newkey rsa:2048 -keyout k.pem -out c.pem -days 1 -nodes -subj '/CN=t' -batch

# 3) 修后通过（退出码 0，产出证书）
OPENSSL_CONF=/dev/null openssl req -x509 -newkey rsa:2048 -keyout k.pem -out c.pem -days 1 -nodes -subj '/CN=t' -batch
```

## 适用边界 / 反例 / 解除条件
- **适用**：`test_package`／消费者脚本以 shell 调用打包版 openssl CLI 且未显式指定配置文件；
  最常见写法就是自助签一张测试证书。
- **反例／不适用**：只调用不读默认配置的子命令（`s_client`、`version`、全参数 `pkey`）；
  上游构建期就用了可迁移相对前缀并随包发布 cnf 的制品。
- **不要用本法的场合**：命令确实需要 cnf 提供 `req_extensions`、`distinguished_name` 等模板字段时，
  `/dev/null` 不满足，须自备最小 cnf 并 `-config` 传入（见兜底方案）。
- **解除条件**：若 openssl 制品改为随包发布 cnf 且把 `OPENSSLDIR` 指向包内相对位置（即可迁移），
  本条不再适用。

## 兜底方案
**方法**: `ship-minimal-cnf-and-pass-config`

在测试目录内生成一份最小 cnf 并显式 `-config` 传入，让测试与默认配置彻底解耦：
```
printf '[req]\ndistinguished_name=dn\n[req_distinguished_name]\n[dn]\nCN=trojan-test\n' > min.cnf
openssl req -config min.cnf -x509 -newkey rsa:2048 -keyout k.pem -out c.pem -days 1 -nodes -batch
```

## 关键词
openssl packaged binary, baked OPENSSLDIR, non-relocatable prefix, openssl.cnf missing,
BIO_new_file, OPENSSL_CONF, consumer test, test_package, conanrun vs buildenv, req -x509

---
*与相近条目的区分：**E006** 是 openssl ARM64 汇编在 RSA-PSS 签名验证上的 bug 及其重建绕过
（机制为签名校验失败，其构建命令里出现 `--openssldir` 只是 Configure 参数）；**E235** 是 openssl
默认 OS 随机源 seeding（随机数路径，非配置文件加载）；**DRAFT-openssl-4.0-major-migration** 是
4.0 大版本迁移中 `OPENSSLDIR` 断言的调整，属版本行为差异。三者与本条（制品内嵌绝对路径不可迁移）
均不同签名、不同修法。`draft-review` 实测 TOP3 相似度 E235=0.03、E006=0.02、E384=0.01，
全部远低于 create 阈值 0.30，质量预检 signature/root_cause/rec 三项全过。*
*实测来源：trojan 1.16.0（本 PR）。设备侧 `conan-verify` 在加 `OPENSSL_CONF=/dev/null` 前
`test()` 退出码 1，加后 `✅ 配方验证通过`（G2/G3/G4 全过，用时 60.6s，峰值内存 592MB）。*
