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
    subprocess.Popen(['emacs', '--script', 'publish.el', HOME_DIR])

# Run html to blog stuff
subprocess.Popen(['python', 'reprise.py'])

# Remove WEB_DIR
shutil.rmtree(WEB_DIR)

# Copy the newly generated stuff
shutil.rmtree(PUB_DIR, WEB_DIR)
