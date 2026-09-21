;;; test_xelb.el --- Consumer functional test for xelb -*- lexical-binding: t; -*-

;; 10 checks against the installed package. Each check signals an error on
;; failure; the final XELB-RESULT line is the single deterministic count
;; source parsed by test_xelb.sh.

(defun test-xelb--packaged-library-p (library version basename)
  (and (stringp library)
       (string-match-p
        (concat (regexp-quote version)
                "/"
                (regexp-quote basename)
                "\\.elc?\\'")
        library)))

;; 1. The xcb library must resolve to the packaged site-lisp directory.
(let ((library (locate-library "xcb")))
  (unless (test-xelb--packaged-library-p library "xelb-0.20" "xcb")
    (error "xcb was not loaded from the packaged lisp dir: %S" library)))

(require 'xcb)
(require 'xelb)

;; 2-3. Entry-point features are provided.
(unless (featurep 'xcb)
  (error "xcb feature was not provided"))
(unless (featurep 'xelb)
  (error "xelb feature was not provided"))

;; 4-7. The binary conversion primitives exist.
(dolist (function '(xcb:-f32-to-binary32
                    xcb:-binary32-to-f32
                    xcb:-f64-to-binary64
                    xcb:-binary64-to-f64))
  (unless (fboundp function)
    (error "%S conversion primitive is not defined" function)))

;; 8. float32 round trip of 1.0 through its IEEE-754 bit pattern.
(unless (= (xcb:-f32-to-binary32 1.0) #x3f800000)
  (error "f32 encoding of 1.0 mismatch: %S" (xcb:-f32-to-binary32 1.0)))
(unless (= (xcb:-binary32-to-f32 #x3f800000) 1.0)
  (error "f32 decoding of 0x3f800000 mismatch"))

;; 9. float64 round trip of 1.0 through its IEEE-754 bit pattern.
(unless (= (xcb:-f64-to-binary64 1.0) #x3ff0000000000000)
  (error "f64 encoding of 1.0 mismatch"))
(unless (= (xcb:-binary64-to-f64 #x3ff0000000000000) 1.0)
  (error "f64 decoding of 0x3ff0000000000000 mismatch"))

;; 10. A generated protocol binding loads from the packaged directory.
(require 'xcb-xproto)
(unless (featurep 'xcb-xproto)
  (error "xcb-xproto feature was not provided"))

(message "XELB-RESULT: passed=10 total=10")

;;; test_xelb.el ends here
