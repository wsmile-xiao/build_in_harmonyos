// test_libabigail.cc — libabigail L1 实质测试（R34）
//
// 真正链接 libabigail 并调用其公共 API：
//   1. abigail::ir::environment     —— 构造 IR 环境（库核心对象）
//   2. abigail::ir::environment::get_void_type() —— 查询内置 void 类型
//   3. abigail::tools_utils::get_library_version_string() —— 查询库版本
#include <iostream>
#include <string>

#include "abg-ir.h"
#include "abg-tools-utils.h"

int main()
{
  // 构造 IR 环境对象（真实调用库代码：创建 canonical type 表等）。
  abigail::ir::environment env;
  abigail::ir::type_base_sptr void_type = env.get_void_type();

  std::string version = abigail::tools_utils::get_library_version_string();
  std::cout << "libabigail version: " << version << std::endl;
  std::cout << "void type: " << (void_type ? "present" : "NULL") << std::endl;

  if (!void_type || version.empty())
    {
      std::cerr << "FAIL: libabigail API returned unexpected result" << std::endl;
      return 1;
    }

  std::cout << "libabigail API test OK" << std::endl;
  return 0;
}
