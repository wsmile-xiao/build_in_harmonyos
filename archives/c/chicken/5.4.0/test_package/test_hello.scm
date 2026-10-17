;; test_hello.scm — real CHICKEN API usage for conan test_package (R34)
;; Exercises: factorial recursion, chicken-version, string-append, error
(import (chicken base)
        (chicken string)
        (chicken platform))

(define (fact n)
  (if (= n 0) 1 (* n (fact (- n 1)))))

(define result (fact 10))
(print "Hello from CHICKEN " (chicken-version))
(print "fact(10) = " result)

(unless (= result 3628800)
  (error "factorial test failed"))

(unless (string=? (string-append "conan" "test") "conantest")
  (error "string test failed"))

(print "conan test_package: chicken toolchain OK")
