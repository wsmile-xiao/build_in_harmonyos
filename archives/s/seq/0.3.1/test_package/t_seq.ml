(* test_package/t_seq.ml — Conan test_package for seq 0.3.1

   Based on upstream test/t.ml: verifies the Seq compatibility module
   by building a lazy sequence 0..10 and folding it with (+), asserting
   the sum equals 55.  A broken seq.cma (missing Seq.fold_left, wrong
   Cons/Nil) cannot pass. *)

let s0_10 : int Seq.t =
  let rec mk i () =
    if i > 10 then Seq.Nil
    else Seq.Cons (i, mk (i + 1))
  in
  mk 0

let () =
  let sum = Seq.fold_left (+) 0 s0_10 in
  Printf.printf "1..1\n";
  Printf.printf "sum: %d\n" sum;
  assert (sum = 55);
  Printf.printf "ok 1 - Seq.fold_left 0..10 = 55\n"
