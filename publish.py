#!/usr/bin/env python
import sys
import subprocess
import shutil
from os.path import abspath, join, dirname, exists

SRC_DIR = join(abspath(dirname(__file__)), 'source')
PUB_DIR = join(abspath(dirname(__file__)), 'public')
HOME_DIR = '/home/punchagan'
WEB_DIR = '/var/www/punchagan.muse-amuse.in'

# --export-org option is passed remove the existing 'source' dir
if len(sys.argv) == 2 and sys.argv[-1] == '--export-org':
    if exists(SRC_DIR):
        shutil.rmtree(SRC_DIR)

# If a 'source' dir is not present, export org to html
if not exists(SRC_DIR):
    export = subprocess.Popen(['emacs', '--script', 'publish.el', HOME_DIR],
                              stdout=subprocess.STDOUT,
                              stderr=subprocess.STDOUT)

    export.wait()

# Run html to blog stuff
publish = subprocess.Popen([sys.executable, 'reprise.py'])
publish.wait()

# Remove WEB_DIR
if exists(WEB_DIR):
    shutil.rmtree(WEB_DIR)

# Copy the newly generated stuff
shutil.copytree(PUB_DIR, WEB_DIR)
