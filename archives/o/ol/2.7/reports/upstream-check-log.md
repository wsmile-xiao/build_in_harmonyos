# ol 2.7 上游测试日志（`make check` 逐字留档）

> 运行期日志不入库（仓库规则禁止 `*.log` 进 PR），逐字转为本文件留档。
> 代码块为原文件**逐字节**复制（含末尾空行），可用 `sha256sum` 复算。
> 原文件由 conanfile.py 的 `build()` 生成：四组各复制一份已构建源码树、在副本里并行跑
> （`language-tests` / `rosettacode-tests` / `ffi-tests` / `check-reference`，各组 -j1），
> 逐组落盘后按固定顺序拼接（用例集合与串行 `make check` 完全一致）。

- 字节数：38581
- 行数：471
- sha256：`526fa8a73e67e4ee7e84b174fad880d917d0d9940f688023334fe5586b52d4e2`
- 计数口径（按分组头切段，逐项配对「测试名行 ↔ 结果行」）：清点 211
  （LANGUAGE 62 / ROSETTRACODE 112 / FFI-Tier-1 7 / FFI-Tier-2 9 / CHECK REFERENCE 21），
  实际运行 210；`tests/fasl-binary.bin` 属上游默认不执行（`extras/check.mk` 的 `%.bin.ok` 规则
  被整段注释、`tmp/check.log` 无其记录），日志中只有名字行没有结果行。
- 末行：`UPSTREAM_MAKE_CHECK_RC=0`

```text
GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
------------------------------------------------------------------------------

tmp/olvm-native-debug:
   /data/service/hnp/bin/clang src/olvm.c extensions/ffi.c -Iincludes -std=gnu99 -Wno-int-to-pointer-cast  -z noexecstack  -DHAVE_SOCKETS=1 -DHAVE_DLOPEN=1 -DHAVE_SECCOMP=1 -fno-exceptions     -fno-unwind-tables -fno-asynchronous-unwind-tables   -DHAVE_MEMFD_CREATE=1 -lm -D_FILE_OFFSET_BITS=64 -O0 -g3 -Wall -DCAR_CHECK=1 -DCDR_CHECK=1 -DNTRACE  -ldl -Xlinker --export-dynamic -o tmp/olvm-native-debug
------------------------------------------------------------------------------

tmp/olvm-native-release:
   /data/service/hnp/bin/clang src/olvm.c extensions/ffi.c -Iincludes -std=gnu99 -Wno-int-to-pointer-cast  -z noexecstack  -DHAVE_SOCKETS=1 -DHAVE_DLOPEN=1 -DHAVE_SECCOMP=1 -fno-exceptions     -fno-unwind-tables -fno-asynchronous-unwind-tables   -DHAVE_MEMFD_CREATE=1 -lm -D_FILE_OFFSET_BITS=64  -O2 -DNDEBUG -Wno-unused-result -g0  -ldl -Xlinker --export-dynamic -o tmp/olvm-native-release
 
# LANGUAGE TESTS
GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| HarmonyOS                                                  | Native  |
|Test                                                        |dbg.|rel.
|tests/apply.scm ............................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/arity-errors.scm .....................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/async.scm ............................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/banana.scm ...........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/bignum.scm ...........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/callcc.scm ...........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/case-apply.scm .......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/case-lambda.scm ......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/circle.scm ...........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/comments.scm .........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/coroutines.scm .......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/data-parse.scm .......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/define-sorted.scm ....................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/echo.scm .............................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ellipsis.scm .........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/eval.scm .............................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/exceptions.scm .......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/factor-rand.scm ......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/factorial.scm ........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/fasl.scm .............................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ff-call.scm ..........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ff-del-rand.scm ......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ff-rand.scm ..........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/fib-rand.scm .........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/foldmap.scm ..........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/hashbang.scm .........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/iff-rand.scm .........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/inexact.scm ..........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/infix-notation.scm ...................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/json.scm .............................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/library.scm ..........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/link.scm .............................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/macro-lambda.scm .....................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/macro-types.scm ......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/mail-order.scm .......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/math-rand.scm ........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/numbers.scm ..........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/opt.scm ..............................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/par-nested.scm .......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/parameterize.scm .....................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/perm-rand.scm ........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/por-nested-rand.scm ..................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/queue-rand.scm .......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/record.scm ...........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/regex.scm ............................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rlist-rand.scm .......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/seven.scm ............................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/share.scm ............................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/stable-rand.scm ......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/str-quote.scm ........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/string.scm ...........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/suffix-rand.scm ......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/syntax-capture.scm ...................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/syntax-lambda.scm ....................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/toplevel-persist.scm .................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/utf-8-rand.scm .......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/vararg.scm ...........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/vector-rand.scm ......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/vectors.scm ..........................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/wait.scm .............................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/world.scm ............................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/fasl-binary.bin ......................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
passed!
UPSTREAM_GROUP_language-tests_RC=0
GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
------------------------------------------------------------------------------

tmp/olvm-native-debug:
   /data/service/hnp/bin/clang src/olvm.c extensions/ffi.c -Iincludes -std=gnu99 -Wno-int-to-pointer-cast  -z noexecstack  -DHAVE_SOCKETS=1 -DHAVE_DLOPEN=1 -DHAVE_SECCOMP=1 -fno-exceptions     -fno-unwind-tables -fno-asynchronous-unwind-tables   -DHAVE_MEMFD_CREATE=1 -lm -D_FILE_OFFSET_BITS=64 -O0 -g3 -Wall -DCAR_CHECK=1 -DCDR_CHECK=1 -DNTRACE  -ldl -Xlinker --export-dynamic -o tmp/olvm-native-debug
------------------------------------------------------------------------------

tmp/olvm-native-release:
   /data/service/hnp/bin/clang src/olvm.c extensions/ffi.c -Iincludes -std=gnu99 -Wno-int-to-pointer-cast  -z noexecstack  -DHAVE_SOCKETS=1 -DHAVE_DLOPEN=1 -DHAVE_SECCOMP=1 -fno-exceptions     -fno-unwind-tables -fno-asynchronous-unwind-tables   -DHAVE_MEMFD_CREATE=1 -lm -D_FILE_OFFSET_BITS=64  -O2 -DNDEBUG -Wno-unused-result -g0  -ldl -Xlinker --export-dynamic -o tmp/olvm-native-release
 
# ROSETTRACODE.ORG OL EXAMPLES
GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| HarmonyOS                                                  | Native  |
|Test                                                        |dbg.|rel.
|tests/rosettacode/100_doors.scm ............................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/99_Bottles_of_Beer.scm ...................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/9_billion_names_of_God_the_integer.scm ...GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/A_star_search_algorithm.scm ..............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/LZW_compression.scm ......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/a+b.scm ..................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/ackermann_function.scm ...................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/anonymous_recursion.scm ..................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/arithmetic_complex.scm ...................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/arithmetic_integer.scm ...................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/arithmetic_rational.scm ..................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/array_length.scm .........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/arrays.scm ...............................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/ascii_art_diagram_converter.scm ..........GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/associative_array+creation.scm ...........GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/associative_array+merging.scm ............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/babbage_problem.scm ......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/base64_decode_data.scm ...................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/base64_encode_data.scm ...................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/binary_digits.scm ........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/call_a_foreign-language_function.scm .....GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/call_a_function.scm ......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/call_a_function_in_a_shared_library.scm ..GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/case-sensitivity_of_identifiers.scm ......GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/comma_quibbling.scm ......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/conditional_structures.scm ...............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/convert_decimal_number_to_rational.scm ...GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/copy_a_string.scm ........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/crc32.scm ................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/currying.scm .............................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/detect_division_by_zero.scm ..............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/determinant_and_permanent.scm ............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/digital_root.scm .........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/dot_product.scm ..........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/empty_program.scm ........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/enumerations.scm .........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/even_or_odd.scm ..........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/execute_brainfuck.scm ....................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/extreme_floating_point_values.scm ........GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/fibonacci_n-step_number_sequences.scm ....GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/filter.scm ...............................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/first-class_functions.scm ................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/fizzbuzz.scm .............................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/flatten_a_list.scm .......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/function_composition.scm .................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/function_definition.scm ..................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/function_prototype.scm ...................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/greatest_common_divisor.scm ..............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/greatest_element_of_a_list.scm ...........GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/happy_numbers.scm ........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/hello_world.scm ..........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/higher-order_functions.scm ...............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/huffman_coding.scm .......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/identity_matrix.scm ......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/include_a_file.scm .......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/infinity.scm .............................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/integer_comparison.scm ...................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/integer_sequence.scm .....................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/isqrt__integer_square_root__of_x.scm .....GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/json.scm .................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/jump_anywhere.scm ........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/knuth_shuffle.scm ........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/letter_frequency.scm .....................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/lexical_analyzer.scm .....................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/longest_common_prefix.scm ................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/loops-break.scm ..........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/loops-foreach.scm ........................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/loops-infinite.scm .......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/man_or_boy_test.scm ......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/mandelbrot_set.scm .......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/matrix_multiplication.scm ................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/maze_generation.scm ......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/multifactorial.scm .......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/mutual_recursion.scm .....................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/nonogram_solver.scm ......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/object_serialization.scm .................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/odd_word_problem.scm .....................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/order_two_numerical_lists.scm ............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/palindrome_detection.scm .................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/pi.scm ...................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/pick_random_element.scm ..................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/population_count.scm .....................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/primality_by_trial_division.scm ..........GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/pythagorean_triples.scm ..................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/range_extraction.scm .....................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/read_entire_file.scm .....................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/regular_expressions.scm ..................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/repeat.scm ...............................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/reverse_a_string.scm .....................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/rot-13.scm ...............................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/run-length_encoding.scm ..................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/set.scm ..................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/short-circuit_evaluation.scm .............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/sieve_of_eratosthenes.scm ................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/sort_an_array_of_composite_structures.scm GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/sort_an_integer_array.scm ................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/sort_using_a_custom_comparator.scm .......GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/special_characters.scm ...................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/stack.scm ................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/sum_and_product_of_an_array.scm ..........GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/sum_digits_of_an_integer.scm .............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/sum_multiples_of_3_and_5.scm .............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/sum_of_squares.scm .......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/synchronous_concurrency.scm ..............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/tree_sort_on_a_linked_list.scm ...........GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/unicode_variable_names.scm ...............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/vector.scm ...............................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/word_wrap.scm ............................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/zero_to_the_zero_power.scm ...............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/sorting_algorithms/bubble_sort.scm .......GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/sorting_algorithms/quicksort.scm .........GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/rosettacode/sorting_algorithms/sleep_sort.scm ........GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
passed!
UPSTREAM_GROUP_rosettacode-tests_RC=0
GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
ol --home=libraries:tests/ffi tests/ffi/src.inc.generator >tests/ffi/src.inc
------------------------------------------------------------------------------

tmp/ffi-native-debug:
   /data/service/hnp/bin/clang src/olvm.c extensions/ffi.c -Iincludes -std=gnu99 -Wno-int-to-pointer-cast  -z noexecstack  -DHAVE_SOCKETS=1 -DHAVE_DLOPEN=1 -DHAVE_SECCOMP=1 -fno-exceptions     -fno-unwind-tables -fno-asynchronous-unwind-tables   -DHAVE_MEMFD_CREATE=1 -lm -D_FILE_OFFSET_BITS=64 tests/ffi/src.c -O0 -g3 -Wall -DCAR_CHECK=1 -DCDR_CHECK=1 -DNTRACE  -ldl -Xlinker --export-dynamic -o tmp/ffi-native-debug
------------------------------------------------------------------------------

tmp/ffi-native-release:
   /data/service/hnp/bin/clang src/olvm.c extensions/ffi.c -Iincludes -std=gnu99 -Wno-int-to-pointer-cast  -z noexecstack  -DHAVE_SOCKETS=1 -DHAVE_DLOPEN=1 -DHAVE_SECCOMP=1 -fno-exceptions     -fno-unwind-tables -fno-asynchronous-unwind-tables   -DHAVE_MEMFD_CREATE=1 -lm -D_FILE_OFFSET_BITS=64 tests/ffi/src.c  -O2 -DNDEBUG -Wno-unused-result -g0  -ldl -Xlinker --export-dynamic -o tmp/ffi-native-release
 
# FFI-Tier-1 TESTS
GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| HarmonyOS                                                  | Native  |
|Test                                                        |dbg.|rel.
|tests/ffi/tier-1/numbers.floats.5-16.scm ...................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-1/numbers.integers.5-16.32b.scm .............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-1/numbers.integers.5-16.64b.scm .............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-1/numbers.mixed-type-args.scm ...............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-1/numbers.mixed-type.5-16.all.scm ...........GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-1/too-much-arguments.scm ....................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-1/variable-arguments.scm ....................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
passed!
 
# FFI-Tier-2 TESTS
GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| HarmonyOS                                                  | Native  |
|Test                                                        |dbg.|rel.
|tests/ffi/tier-2/longs.scm .................................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-2/numbers.floats.1-4.scm ....................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-2/numbers.integers.1-4.32b.scm ..............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-2/numbers.integers.1-4.64b.scm ..............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-2/numbers.mixed-type.2-4.all.scm ............GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-2/paramless.floats.scm ......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-2/paramless.integers.32b.scm ................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-2/paramless.integers.64b.scm ................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
|tests/ffi/tier-2/wide-characters.scm .......................GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
| ok | ok |
passed!
UPSTREAM_GROUP_ffi-tests_RC=0
GNUmakefile:80: Submodules not loaded. Run 'git submodule update --init --recursive' once.
------------------------------------------------------------------------------

tmp/olvm-native-debug:
   /data/service/hnp/bin/clang src/olvm.c extensions/ffi.c -Iincludes -std=gnu99 -Wno-int-to-pointer-cast  -z noexecstack  -DHAVE_SOCKETS=1 -DHAVE_DLOPEN=1 -DHAVE_SECCOMP=1 -fno-exceptions     -fno-unwind-tables -fno-asynchronous-unwind-tables   -DHAVE_MEMFD_CREATE=1 -lm -D_FILE_OFFSET_BITS=64 -O0 -g3 -Wall -DCAR_CHECK=1 -DCDR_CHECK=1 -DNTRACE  -ldl -Xlinker --export-dynamic -o tmp/olvm-native-debug
------------------------------------------------------------------------------

tmp/olvm-native-release:
   /data/service/hnp/bin/clang src/olvm.c extensions/ffi.c -Iincludes -std=gnu99 -Wno-int-to-pointer-cast  -z noexecstack  -DHAVE_SOCKETS=1 -DHAVE_DLOPEN=1 -DHAVE_SECCOMP=1 -fno-exceptions     -fno-unwind-tables -fno-asynchronous-unwind-tables   -DHAVE_MEMFD_CREATE=1 -lm -D_FILE_OFFSET_BITS=64  -O2 -DNDEBUG -Wno-unused-result -g0  -ldl -Xlinker --export-dynamic -o tmp/olvm-native-release
 
# CHECK REFERENCE
| HarmonyOS                                                  | Native  |
|Test                                                        |dbg.|rel.
|doc/reference/README.md ....................................| ok | ok |
|doc/reference/async.md .....................................| ok | ok |
|doc/reference/booleans.md ..................................| ok | ok |
|doc/reference/bytevectors.md ...............................| ok | ok |
|doc/reference/characters.md ................................| ok | ok |
|doc/reference/equivalence-predicates.md ....................| ok | ok |
|doc/reference/exceptions.md ................................| ok | ok |
|doc/reference/ffs.md .......................................| ok | ok |
|doc/reference/infix-notation.md ............................| ok | ok |
|doc/reference/json.md ......................................| ok | ok |
|doc/reference/lazy-evaluations.md ..........................| ok | ok |
|doc/reference/macros.md ....................................| ok | ok |
|doc/reference/numbers.md ...................................| ok | ok |
|doc/reference/numerical-operations.md ......................| ok | ok |
|doc/reference/pairs-and-lists.md ...........................| ok | ok |
|doc/reference/regex.md .....................................| ok | ok |
|doc/reference/serialization-deserialization.md .............| ok | ok |
|doc/reference/sorting.md ...................................| ok | ok |
|doc/reference/symbols.md ...................................| ok | ok |
|doc/reference/tips-and-tricks.md ...........................| ok | ok |
|doc/reference/vectors.md ...................................| ok | ok |
................passed!
UPSTREAM_GROUP_check-reference_RC=0
UPSTREAM_MAKE_CHECK_RC=0
```
