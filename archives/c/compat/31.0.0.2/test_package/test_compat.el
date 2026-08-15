;;; test_compat.el --- Consumer load test for compat -*- lexical-binding: t; -*-

(let ((library (locate-library "compat")))
  (unless (and (stringp library)
               (string-match-p "compat-31\\.0\\.0\\.2/compat\\.el\\'" library))
    (error "compat library was not loaded from the packaged lisp dir: %S" library)))

(require 'compat)

(unless (featurep 'compat)
  (error "compat feature was not provided"))

(unless (fboundp 'compat-function)
  (error "compat-function is not defined"))

(let ((symbol (compat-function plist-get)))
  (unless (and symbol (symbolp symbol))
    (error "compat-function returned an invalid symbol: %S" symbol)))

(message "compat consumer load validation OK")

;;; test_compat.el ends here
