// bad.cpp — consumer test fixture with deliberate style violations.
// 违规点（对应 kwstyle-config.kws.xml 的 LineLength=120 与 Tabs=1）：
//   1. 第 7 行以制表符缩进（Tab 规则命中）
//   2. 第 7 行超过 120 列（LineLength 规则命中）
int bad_function()
{
	return 42; /* this line is deliberately indented with a tab character and then padded with a very long trailing comment so that it exceeds the configured maximum line length of 120 columns */
}
