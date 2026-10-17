; test_package/harness.scm — consumer checks for the installed ol interpreter.
;
; Otus Lisp is purely functional (no set!), so the failure count is folded over
; the list of check results and the process exit code carries the verdict.
(import (owl math))
(import (scheme base))

(define (check name actual expected)
   (if (equal? actual expected)
      (begin (print "PASS: " name) 0)
      (begin (print "FAIL: " name " actual=" actual " expected=" expected) 1)))

(define failures
   (apply + (list
      (check "arith" (+ 1 2 39) 42)
      (check "mul" (* 6 7) 42)
      (check "string-append" (string-append "otus" "-" "lisp") "otus-lisp")
      (check "string-length" (string-length "Otus Lisp") 9)
      (check "list-map" (map (lambda (x) (* x x)) '(1 2 3 4)) '(1 4 9 16))
      (check "factorial" (let loop ((n 5) (acc 1)) (if (eq? n 0) acc (loop (- n 1) (* acc n)))) 120)
      (check "gcd" (gcd 48 18) 6))))

(print "harness: failures=" failures)
(exit (if (= failures 0) 0 1))
