#!/usr/bin/emacs --script
(setq home-dir "/home/punchagan/")

(add-to-list 'load-path (expand-file-name
                         ".emacs.d/elisp/org/lisp/"
                         home-dir))
;; Added for htmlize
(add-to-list 'load-path (expand-file-name
                         ".emacs.d/elisp/org/contrib/lisp"
                         home-dir))

;; Load up Org Mode and Babel
(require 'org-install)

(add-to-list 'load-path "~/blog-files/")
(require 'org-reprise)

(setq org-export-htmlize-output-type 'css)
(setq org-export-babel-evaluate nil)

(org-babel-do-load-languages
 'org-babel-load-languages
 '((python . t)
   (emacs-lisp . t)
   ))

(require 'org-publish)

(setq org-publish-project-alist
      '(
	("org-notes"
	 :base-extension "org"
	 :base-directory "~/.life-in-plain-text/"
	 :publishing-directory "~/blog-files/assests/"
	 :blog-publishing-directory "~/blog-files/"
	 :site-root "http://punchagan.muse-amuse.in"
	 :hyde-sanitize-permalinks t
	 :recursive t
	 :publishing-function org-publish-org-to-html
	 :headline-levels 4             ; Just the default for this project.
	 :auto-postamble nil
	 :auto-preamble t
	 :exclude-tags ("ol" "noexport")
	 )

	("org-static"
	 :base-directory "~/.life-in-plain-text/"
	 :publishing-directory "~/blog-files/assets/media/"
	 :base-extension "css\\|js\\|png\\|jpg\\|gif\\|pdf\\|mp3\\|ogg\\|swf"
	 :recursive t
	 :publishing-function org-publish-attachment
	 )

	("org" :components ("org-notes" "org-static"))

	))


(defun publish-blog ()
  (interactive)
  (org-reprise-export-blog "~/.life-in-plain-text/notes.org"))

(shell-command "rm -rf ~/blog-files/source/")
(publish-blog)

(shell-command (expand-file-name
                "pub-site/bin/python ~/blog-files/reprise.py"
                home-dir))

(shell-command "cp -a ~/blog-files/public/* /var/www/punchagan.muse-amuse.in")
