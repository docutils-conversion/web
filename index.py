#! /usr/bin/env python

import templater

templater.main('index.html.template', '../restructuredtext/spec',
               ['introduction.txt', 'reStructuredText.txt', 'pyextensions.txt',
                'problems.txt', 'rst-notes.txt'])
