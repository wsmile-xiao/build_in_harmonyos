(* test_package/t_pagodacf.ml — Conan test_package for pagodacf 0.1

   This test program exercises the OCaml NAE Core Foundation (Cf) library
   by calling real Cf APIs: the functional red-black tree map/set, the
   lazy sequence, and the real-time catenable deque. Each sub-test uses
   `assert` on a computed result, so a wrong library build cannot pass.
 *)
open Printf

(* ---- Test 1: Cf_rbtree.Map functor with Cf_ordered.Int_order ---- *)
module IntMap = Cf_rbtree.Map(Cf_ordered.Int_order)

let test_rbtree () =
  let m =
    List.fold_left (fun acc (k, v) -> IntMap.replace (k, v) acc)
      IntMap.nil
      [(1, "one"); (2, "two"); (3, "three"); (4, "four")]
  in
  (* search raises Not_found for missing keys, returns the value otherwise *)
  assert (IntMap.search 2 m = "two");
  assert (IntMap.search 3 m = "three");
  assert (IntMap.member 4 m);
  assert (not (IntMap.member 9 m));
  (* size of a map with 4 bindings must be 4 *)
  assert (IntMap.size m = 4);
  (* delete a key and check size drops *)
  let m' = IntMap.delete 1 m in
  assert (IntMap.size m' = 3);
  assert (not (IntMap.member 1 m'));
  printf "[ok] Cf_rbtree.Map (Int_order): replace/search/member/delete/size\n%!"

(* ---- Test 2: Cf_seq functional lazy sequences ---- *)
let test_seq () =
  let s = Cf_seq.of_list [10; 20; 30; 40; 50] in
  (* Fold to sum the elements *)
  let sum = Cf_seq.fold (fun acc x -> acc + x) 0 s in
  assert (sum = 150);
  (* length of a 5-element sequence must be 5 *)
  assert (Cf_seq.length s = 5);
  (* to_list round-trip *)
  let l = Cf_seq.to_list s in
  assert (l = [10; 20; 30; 40; 50]);
  printf "[ok] Cf_seq: of_list/fold/length/to_list\n%!"

(* ---- Test 3: Cf_deque real-time catenable deque ---- *)
(* Cf_deque's push/pop live in the Direction_T submodules A (left end) and
   B (right end), not at the top level. Using A.push (left) + B.pop (right)
   gives FIFO queue semantics: the deque drains in the same order the
   elements were pushed. This mirrors upstream t_cf.ml's test pattern
   (`test1 A.pop B.push` / `test1 B.pop A.push`). *)
let test_deque () =
  let q = Cf_deque.nil in
  let q = Cf_deque.A.push 1 q in
  let q = Cf_deque.A.push 2 q in
  let q = Cf_deque.A.push 3 q in
  (* B.pop returns (head, tail) option; drain all three elements (FIFO) *)
  let rec drain acc q =
    match Cf_deque.B.pop q with
    | None -> List.rev acc
    | Some (x, q') -> drain (x :: acc) q'
  in
  let got = drain [] q in
  assert (got = [1; 2; 3]);
  (* after draining, the deque is empty *)
  assert (Cf_deque.empty Cf_deque.nil);
  printf "[ok] Cf_deque: nil/A.push/B.pop/empty\n%!"

(* ---- Test 4: Cf_rbtree.Set functor ---- *)
module IntSet = Cf_rbtree.Set(Cf_ordered.Int_order)

let test_set () =
  let s =
    List.fold_left (fun acc x -> IntSet.put x acc)
      IntSet.nil [1; 2; 3; 2; 1]
  in
  (* duplicates are collapsed: 3 unique elements *)
  assert (IntSet.size s = 3);
  assert (IntSet.member 2 s);
  assert (not (IntSet.member 9 s));
  (* ascending order list *)
  assert (IntSet.to_list_incr s = [1; 2; 3]);
  printf "[ok] Cf_rbtree.Set (Int_order): put/member/size/to_list_incr\n%!"

(* ---- Test 5: Unix.getpid forces dllunix.so load ---- *)
(* dllcf.so (Cf's C stub) relocates `unix_error` from OCaml's `unix`
   library C stub `dllunix.so` (cf_tai64n_p.c:190 calls it on
   gettimeofday failure). The bytecode linker only `dlopen`s a .cma's
   stub dll when one of its primitives is *referenced* in the linked
   code; an unreferenced .cma is dead-stripped and its dll is neither
   loaded at link time nor embedded in the executable header. Our
   Tests 1-4 use only pure Cf core modules, so without an explicit
   `Unix.` reference `ocamlc` would not load `dllunix.so`, and the
   runtime `ocamlrun` would fail to relocate `dllcf.so` with
   `unix_error: symbol not found`. Calling `Unix.getpid ()` here
   mirrors upstream t_cf.ml's 12 `Unix.` references: it forces
   `ocamlc` to `dlopen` `dllunix.so` at link time (so the executable
   header embeds `dllunix.so` before `dllcf.so`), and at runtime
   `ocamlrun` `dlopen`s `dllunix.so` first, registering `unix_error`
   globally before `dllcf.so` is relocated. `Unix.getpid` is the most
   benign Unix primitive: it wraps `getpid(2)`, always succeeds, and
   returns the positive PID of the test process. *)
let test_unix_load () =
  let pid = Unix.getpid () in
  assert (pid > 0);
  printf "[ok] Unix.getpid: dllunix.so loaded (pid=%d)\n%!" pid

let () =
  let tests = [test_rbtree; test_seq; test_deque; test_set; test_unix_load] in
  printf "1..%d\n" (List.length tests);
  let n = ref 0 in
  List.iter (fun f -> incr n; f (); printf "ok %d\n" !n) tests
