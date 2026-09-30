project('test_litexl', 'c',
  version: '2.1.8',
  default_options: ['c_std=gnu11'])

# 测试程序只依赖 libc（fork/exec/poll/waitpid），经 MesonToolchain 交叉编译。
test_litexl = executable('test_litexl',
  'test_litexl.c',
  install: false)
