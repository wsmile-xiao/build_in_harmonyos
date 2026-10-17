"""Sample unformatted source file used by test_package.

black should reformat this file to canonical style: the dict literal at the
bottom must be collapsed onto a single line with normalized spacing.

The test asserts the formatted result, so it substantively exercises
the packaged formatter (R34), not just `--version`.
"""


def f(x):
    return x


x = {  "a":1,
   "b": 2}
