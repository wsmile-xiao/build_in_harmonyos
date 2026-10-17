// test_package/hello.vala — 实质调用被测包 valac（R34）
// 由 test_package/conanfile.py 用 valac 编译并运行本文件，
// 校验输出必须包含 "Hello from vala 0.56.19"。
void main () {
    stdout.printf ("Hello from vala 0.56.19 on OHOS!\n");
}
