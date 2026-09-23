# enigma

Perl 模块，二战 Enigma 密码机的纯 Perl 实现（上游 CPAN 分发 `Crypt-Enigma`，
模块 `Crypt::Enigma`）。

## 主要功能

- `Crypt::Enigma->new([\%args])` — 创建密码机（rotors / startletters /
  ringsettings / reflector / stecker 可配）
- `$enigma->cipher($text)` — 加密/解密（反射体为对合，同一调用往返）
- `$enigma->setSteckerBoard([...])` — 插线板配对，即时生效
- `$enigma->setReflector($name)` — 切换反射体（非法名回退 ReflectorB）
- `$enigma->setRotor($name, $letter, $ring, $n)` — 登记转子定义
  （返回 1 成功 / 0 拒绝）
- `getRotorNames / getStartLetters / getRingSettings / getReflector /
  dumpSettings / setDebug` — 查询与调试
- 零外部依赖：纯 Perl，仅需系统 `perl` + `make`

## 编译指导

纯 Perl 模块，使用 Makefile.PL 构建，无需 C 编译器：

```bash
perl Makefile.PL
make
make test  # 上游 t/01.t，共 1 个测试
make install DESTDIR=/tmp/destdir
# 复制 .pm 到标准位置
cp /tmp/destdir/.../Crypt/Enigma.pm lib/perl5/Crypt/Enigma.pm
```

### HarmonyOS 注意事项

- 纯 Perl 模块，不受 SELinux/HMDFS 限制，经 `PERL5LIB` 直接使用。
- 无外部依赖；`generate()` 注入 `TMPDIR=<build_folder>` 规避 /tmp 只读（E002）。
- `build()` 解析 `make test` 真实输出落盘 `res/upstream_test_result.json`，
  test 阶段原样重发，杜绝"退出码 0 即通过"的误判。
- 上游 1.3 已知 quirk（不打补丁，原样记录）：构造函数不预存 rotor 对象、
  非零 ring 或"先 setRotor 再 cipher"路径不可用；测试只覆盖可用的
  确定性语义（详见 `1.3/notes.md`）。

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.3](./1.3/)（上游 Crypt-Enigma 1.3） | built（首轮工作树，待真机验证） | 2026-09-09 |
