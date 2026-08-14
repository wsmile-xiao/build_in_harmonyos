;;; test_org.el --- Consumer load test for Org -*- lexical-binding: t; -*-

(let ((library (locate-library "org")))
  (unless (and (stringp library)
               (string-match-p "org-9\\.8\\.8/org\\.el\\'" library))
    (error "org library was not loaded from the packaged lisp dir: %S" library)))

(let ((library (locate-library "ol")))
  (unless (and (stringp library)
               (string-match-p "org-9\\.8\\.8/ol\\.el\\'" library))
    (error "ol library was not loaded from the packaged lisp dir: %S" library)))

(require 'org)
(require 'ol)

(unless (featurep 'org)
  (error "org feature was not provided"))

(unless (featurep 'ol)
  (error "ol feature was not provided"))

(unless (string= (org-version) "9.8.8")
  (error "unexpected org-version: %S" (org-version)))

(unless (fboundp 'org-link-set-parameters)
  (error "org-link-set-parameters is not defined"))

(let ((entry (assoc "https" org-link-parameters)))
  (unless entry
    (error "https org-link type is not registered in org-link-parameters"))
  (unless (listp (cdr entry))
    (error "https org-link parameters are not a list: %S" (cdr entry))))

(message "org consumer load validation OK")

;;; test_org.el ends here
