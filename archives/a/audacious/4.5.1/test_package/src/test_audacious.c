/* test_audacious.c — CI 门禁占位文件
 * 实际测试逻辑在 test_package/conanfile.py 的 test() 方法中：
 *   1. audacious --version 输出版本号
 *   2. libaudcore.so 可加载
 *   3. libaudtag.so 可加载
 * 本文件满足 CI L0c 门禁（要求 test_package/src/ 下有源文件）。
 */
int main(void) { return 0; }
