// test_package — 消费者视角验证 BALL 核心库可链接、可调用 (R34 非空壳)
// 真实调用 BALL 公共 API: GlobalInitializer::init() 初始化 + BALL::String 字符串操作。
#include <BALL/COMMON/init.h>
#include <BALL/DATATYPE/string.h>
#include <iostream>

int main()
{
	// 初始化 BALL 全局环境（静态单例，注册日志/插件路径等）
	BALL::GlobalInitializer* gi = BALL::GlobalInitializer::init();
	(void)gi;

	// 使用 BALL::String 做真实的字符串处理（toUpper 为就地修改，返回 void）
	BALL::String s("BALL");
	s += "-1.5.0";
	s.toUpper();

	if (s == "BALL-1.5.0")
	{
		std::cout << "test ball 1.5.0-git20220524.d85d2dd: OK (" << s << ")" << std::endl;
		return 0;
	}

	std::cerr << "test ball: FAILED (unexpected string: " << s << ")" << std::endl;
	return 1;
}
