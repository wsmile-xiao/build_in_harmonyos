(* mlgmp test_package — 消费者视角验证 Gmp 模块 API
   覆盖 Z (GMP 整数) / Q (有理数) / F (GMP 浮点) / FR (MPFR 浮点)
   使用与上游 test_suite.ml 一致的 API *)
open Gmp

let () =
  (* Z *)
  assert (Z.to_string (Z.add (Z.of_int 40) (Z.of_int 2)) = "42");
  assert (Z.to_string (Z.pow_ui (Z.of_int 2) 10) = "1024");
  assert (Z.is_probab_prime (Z.of_int 7919) 20);
  (* 64-bit 回归（Debian #573978）：OCaml int 为 63 位，Int_val 会截断为 32 位，
     导致 >= 2^31 的实参静默算错；修复后走 Long_val。以下断言在修复前均失败 *)
  assert (Z.to_string (Z.of_int (1 lsl 40)) = "1099511627776");
  assert (Z.to_string (Z.pow_ui (Z.of_int 2) 40) = "1099511627776");
  assert (Z.to_string (Z.ui_pow_ui 2 40) = "1099511627776");
  assert (Z.to_string (Z.mul_2exp (Z.of_int 1) 40) = "1099511627776");
  assert (Z.to_string (Z.tdiv_q_ui (Z.of_int (1 lsl 40)) (1 lsl 31)) = "512");
  assert (Z.to_string (Z.bin_uiui ~n:(1 lsl 33) ~k:1) = "8589934592");
  assert (Z.compare_si (Z.of_int (1 lsl 40)) (1 lsl 40) = 0);
  (* Q *)
  assert (Q.to_string (Q.div (Q.from_ints 1 2) (Q.from_ints 3 4)) = "2/3");
  (* F *)
  let f = F.from_float 3.25 in
  assert (F.to_float f = 3.25);
  (* FR (MPFR) *)
  assert (FR.is_available ());
  let fr = FR.from_float 3.25 in
  assert (FR.to_float fr = 3.25);
  print_endline "mlgmp test_package: Gmp (Z/Q/F/FR) OK"
