# -*- coding: utf-8 -*-
#!/usr/bin/env python

# The original code is available at https://github.com/uggedal/reprise

from __future__ import with_statement

import os
import re
import email
import shutil

from os.path import abspath, dirname, join, exists
from datetime import datetime
from pygments.formatters import HtmlFormatter
from jinja2 import DictLoader, Environment
from lxml.builder import ElementMaker
from lxml.etree import tostring

URL = 'http://punchagan.muse-amuse.in'
STYLESHEET = 'style.css'

PYG_CSS = 'emacs'
NO_EXPORT_TAGS = ['ol', 'noexport']

# Type 1 categories are written to the index.html file.  You can have
# only one category of type-1.  Type 2 categories, are published to a
# different category.html file where category is the name of the
# category.
CATEGORIES = {'blog': {
               'type': 1,
               'title': 'Blog'},
              'links': {
               'type': 2,
               'title': 'Bookmarks'},
              'quotes': {
               'type': 2,
               'title': 'Quotes'}}

AUTHOR = {
    'title': 'Rustic Reverie',
    'name': 'punchagan',
    'email': 'punchagan [at] muse-amuse [dot] in',
    'url': 'http://punchagan.muse-amuse.in',
    'links': [
        ('blog', 'http://punchagan.muse-amuse.in/'),
        ('bookmarks', 'http://punchagan.muse-amuse.in/links'),
        ('quotes', 'http://punchagan.muse-amuse.in/quotes'),
        ('tags', 'http://punchagan.muse-amuse.in/tags'),
        ('feeds', 'http://punchagan.muse-amuse.in/feeds'),
        ('github', 'https://github.com/punchagan'),
        ('projects', 'http://punchagan.muse-amuse.in/projects'),
        ('twitter', 'http://twitter.com/punchagan/'),
        ],
}

ROOT = abspath(dirname(__file__))
DIRS = {
    'source': join(ROOT, 'source'),
    'build': join(ROOT, 'build'),
    'public': join(ROOT, 'public'),
    'assets': join(ROOT, 'assets'),
    'templates': join(ROOT, 'templates'),
}

CONTEXT = {
    'author': AUTHOR,
    'stylesheet': STYLESHEET,
    'head_title': "%s" % (AUTHOR['title']),
    'body_title': "%s" % (AUTHOR['title']),
    'analytics': 'UA-21111013-1',
}

def read_and_parse_entries(category):
    """ Given a category, returns all entries belonging to that category.

    """
    entries = []
    pwd = join(DIRS['source'], category)
    files = [join(pwd,f) for f in os.listdir(pwd) if f.endswith('.txt')]
    for file in files:
        with open(file, 'r') as open_file:
            msg = email.message_from_file(open_file)
            date = datetime(*map(int, msg['Created'].split(':')))
            entries.append({
                'slug': "%s/%s" % (category, slugify(msg['Title'].decode('utf-8'))),
                'title': msg['Title'].decode('utf-8'),
                'tags': process_tags(msg),
                'date': {'iso8601': date.isoformat(),
                         'rfc3339': rfc3339(date),
                         'display': date.strftime('%Y-%m-%d'),},
                'content_html': msg.get_payload().decode('utf-8')
            })
    entries = sorted(entries, key = lambda x: x['date']['iso8601'],
                     reverse = True)
    return entries

def process_tags(msg):
    """ Processes the tags for the message.

    Filters out the tags listed in NO_EXPORT_TAGS, lower cases and sorts
    other tags.
    """
    if 'Tags' in msg.keys():
        tags = sorted(msg['Tags'].lower().split())
        tags = [t for t in tags if t not in NO_EXPORT_TAGS]
    return tags

def generate_index(entries, template, category):
    """ Generates a listing/index and an atom feed for given category.

    """
    # Page name is category.html for type-2 categories and index.html for type-1
    index = category if CATEGORIES[category]['type'] == 2 else 'index'
    feed_url = "%s/%s.atom" % (URL, category)
    body_title = "%s - %s" % (AUTHOR['title'], CATEGORIES[category]['title'])
    head_title = "%s - %s" % (AUTHOR['title'], CATEGORIES[category]['title'])
    html = template.render(dict(CONTEXT, **{'entries': entries,
                                            'feed_url': feed_url,
                                            'body_title': body_title,
                                            'head_title': head_title,
                                            'listing': index != 'index',
                                            }))
    write_file(join(DIRS['build'],
                    category if CATEGORIES[category]['type'] == 1 else '',
                    '%s.html' % index), html)
    atom = generate_atom(entries, feed_url)
    write_file(join(DIRS['build'], '%s.atom' % category), atom)

def generate_tag_indices(entries, template):
    """ Generates an index page and feed page for each tag in entries.

    """
    entries = sorted(entries, key = lambda x: x['date']['iso8601'],
                     reverse = True)
    for tag in set(sum([e['tags'] for e in entries], [])):
        tag_entries = [e for e in entries if tag in e['tags']]
        feed_url = "%s/tags/%s.atom" % (URL, tag)
        html = template.render(
            dict(CONTEXT, **{'entries': tag_entries,
                             'active_tag': tag,
                             'feed_url': feed_url,
                             'body_title': "%s - %s" % (CONTEXT['body_title'],
                                                       tag),
                             'head_title': "%s: %s" % (CONTEXT['head_title'],
                                                       tag),}))

        write_file(join(DIRS['build'], 'tags', '%s.html' % tag), html)
        atom = generate_atom(tag_entries, feed_url)
        write_file(join(DIRS['build'], 'tags', '%s.atom' % tag), atom)

def generate_tag_cloud(entries, template):
    """ Generates a html tag cloud.

    """
    tags = sum([e['tags'] for e in entries], [])
    tag_freq = [{'tag': tag, 'freq': tags.count(tag)} for tag in set(tags)
                if tags.count(tag) > 3]
    if len(tag_freq) > 0:
        maxFreq = max(t['freq'] for t in tag_freq)
        minFreq = min(t['freq'] for t in tag_freq)
        font_range = (80, 320)
        def normalize(val, min_f=minFreq, max_f=maxFreq, f_range=font_range):
            min_r, max_r = f_range
            return min_r + (val - min_f) * (max_r - min_r) / float (max_f - min_f)
        tag_freq = [{'tag': t['tag'],
                    'size': normalize(t['freq']),
                    'freq': t['freq']} for t in tag_freq]
        html = template.render(
            dict(CONTEXT, **{'tag_freq': tag_freq,
                            'head_title': "%s: %s" % (CONTEXT['head_title'],
                                                    'Tag Cloud')}))
        write_file(join(DIRS['build'], 'tags.html'), html)


def generate_details(entries, template):
    for entry in entries:
        html = template.render(
            dict(CONTEXT, **{'entry': entry,
                             'body_title': "%s - %s"
                             % (CONTEXT['body_title'],
                                entry['slug'].split('/')[0].capitalize()),
                             'head_title': "%s: %s" % (CONTEXT['head_title'],
                                                       entry['title'])}))
        write_file(join(DIRS['build'], '%s.html' % entry['slug']), html)


def generate_index_static(entries, template):
    for entry in entries:
        html = template.render(
            dict(CONTEXT, **{'entry': entry,
                             'head_title': "%s: %s" % (CONTEXT['head_title'],
                                                       entry['title'])}))
        write_file(join(DIRS['build'], '%s.html' %
                        entry['slug'][7:]), html)

def generate_404(template):
        html = template.render(CONTEXT)
        write_file(join(DIRS['build'], '404.html'), html)

def generate_style(css):
    css2 = HtmlFormatter(style=PYG_CSS).get_style_defs()
    write_file(join(DIRS['build'], STYLESHEET), ''.join([css, "\n\n", css2]))

def generate_atom(entries, feed_url):
    A = ElementMaker(namespace='http://www.w3.org/2005/Atom',
                     nsmap={None : "http://www.w3.org/2005/Atom"})
    entry_elements = []
    for entry in entries:
        entry_elements.append(A.entry(
            A.id(atom_id(entry=entry)),
            A.title(entry['title']),
            A.link(href="%s/%s" % (URL, entry['slug'])),
            A.updated(entry['date']['rfc3339']),
            A.content(entry['content_html'], type='html'),))
    return tostring(A.feed(A.author( A.name(AUTHOR['name']) ),
                           A.id(atom_id()),
                           A.title(AUTHOR['title']),
                           A.link(href=URL),
                           A.link(href=feed_url, rel='self'),
                           A.updated(entries[0]['date']['rfc3339']),
                           *entry_elements), pretty_print=True)

def write_file(file_name, contents):
    with open(file_name, 'w') as open_file:
        open_file.write(contents.encode('utf-8'))

def slugify(str):
    str = re.sub(r'\s+', '-', re.sub(r'[^\w\s-]', '',
                                      str.lower()))
    return re.sub('-+', '-', str.strip('-'))

def atom_id(entry=None):
    domain = re.sub(r'http://([^/]+).*', r'\1', URL)
    if entry:
        return "tag:%s,%s:/%s" % (domain, entry['date']['display'],
                                  entry['slug'])
    else:
        return "tag:%s,2009-03-04:/" % domain

def rfc3339(date):
    return date.strftime('%Y-%m-%dT%H:%M:%SZ')

def get_templates():
    files = ['base.html', 'list.html', 'detail.html', '_entry.html',
             '404.html', 'static.html', 'cloud.html', STYLESHEET]
    return dict([(f, open("%s/%s" %(DIRS['templates'], f)).read().strip())
                 for f in files])


if __name__ == "__main__":
    templates = get_templates()
    env = Environment(loader=DictLoader(templates))

    shutil.copytree(DIRS['assets'], DIRS['build'])

    if not exists(DIRS['public']):
        os.makedirs(DIRS['public'])

    all_entries = {}
    for c in CATEGORIES:
        print "Parsing Entries in %s ..." % c
        all_entries[c] = read_and_parse_entries(c)
        os.mkdir(join(DIRS['build'], c))
        entries = all_entries[c]

        if entries:
            generate_index(entries, env.get_template('list.html'), c)
            print "Generated index for %s." % c
            print "Generating details for %s ..." % c
            generate_details(entries, env.get_template('detail.html'))

    entries = read_and_parse_entries('static')
    generate_index_static(entries, env.get_template('static.html'))

    os.mkdir(join(DIRS['build'], 'tags'))
    print "Generating Tag indices..."
    generate_tag_indices(sum(all_entries.values(), []),
                         env.get_template('list.html'))

    generate_tag_cloud(sum(all_entries.values(), []),
                       env.get_template('cloud.html'))

    generate_404(env.get_template('404.html'))
    generate_style(templates[STYLESHEET])

    shutil.rmtree(DIRS['public'])
    shutil.move(DIRS['build'], DIRS['public'])
    print "Published!"
