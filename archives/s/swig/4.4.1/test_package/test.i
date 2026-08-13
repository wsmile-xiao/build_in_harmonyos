/* test.i — SWIG interface file for test_package
 * Exercises swig's core code generation functionality (R34)
 */
%module test

%{
int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}
%}

int add(int a, int b);
int multiply(int a, int b);
