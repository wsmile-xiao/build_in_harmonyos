(* test_stdlib_shims.ml — Verify stdlib-shims is usable *)
let _ = Stdlib.(+)
let _ = Stdlib.List.map
let () = print_endline "stdlib-shims OK"
