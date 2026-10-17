import wcwidth

assert wcwidth.__version__ == "0.2.12"
assert wcwidth.wcwidth("a") == 1
assert wcwidth.wcwidth("界") == 2
assert wcwidth.wcwidth("\u0301") == 0
assert wcwidth.wcswidth("hello") == 5
assert wcwidth.wcswidth("你好") == 4
print("wcwidth consumer checks: 6/6 passed")
