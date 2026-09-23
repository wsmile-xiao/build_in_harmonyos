/*
 * C support function for the GNUstep SQLClient 1.9.0 consumer test.
 *
 * 由 test_sqlclient.m 在 main() 中真实引用（check 断言其返回值 == 42），
 * 非门禁占位死代码；同时满足 L0c 测试源门禁（test_package/ 下须含 .c 源文件）。
 */
int gnustep_sql_test_support_value(void)
{
  return 42;
}