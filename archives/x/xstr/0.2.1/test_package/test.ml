(* xstr 0.2.1 test_package — 消费者测试
 *
 * 真实调用 xstr 库的三个模块 API 并断言已知结果（R34：非空壳测试）。
 * 逐条计数的断言，末尾打印 xstr: N/M assertions passed；
 * 任一断言失败则退出码非 0（test_package 的 HMBS_TEST_PACKAGE_RESULT
 * 数字由 test() 解析此行真实得出）。
 *)
let total = ref 0
let passed = ref 0

let check name cond =
  incr total;
  if cond then (
    incr passed;
    Printf.printf "[ok]   %s\n" name)
  else Printf.printf "[FAIL] %s\n" name

let () =
  (* Xstr_search：子串搜索 / 替换 *)
  check "contains_substring"
    (Xstr_search.contains_substring "hello world" "world");
  check "index_of_substring"
    (Xstr_search.index_of_substring "hello world" "world" = 6);
  check "rindex_of_substring"
    (Xstr_search.rindex_of_substring "abab" "ab" = 2);
  check "indexlist_of_substring"
    (Xstr_search.indexlist_of_substring "ababa" "aba" = [ 0; 2 ]);
  check "rev_concat" (Xstr_search.rev_concat " " [ "a"; "b" ] = "b a");

  (* Xstr_split：字符串切分（与 xstr_split.mli 文档示例完全一致） *)
  check "split_string basic"
    (Xstr_split.split_string " " true true [ "," ] "a, b, c ,d "
    = [ "a"; "b"; "c"; "d" ]);
  check "split_string no-ignore"
    (Xstr_split.split_string "" true true [ "," ] "a, b, c ,d "
    = [ "a"; " b"; " c "; "d " ]);

  (* Xstr_match：模式匹配 *)
  check "match literal"
    (Xstr_match.match_string [ Xstr_match.Literal "abc" ] "abc");
  check "match literal fail"
    (not (Xstr_match.match_string [ Xstr_match.Literal "abc" ] "abd"));

  Printf.printf "\nxstr: %d/%d assertions passed\n" !passed !total;
  if !passed = !total then exit 0 else exit 1
