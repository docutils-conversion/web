#! /usr/bin/env python

import templater

templater.main('index.html.template', '../dps/spec',
               ['pep-0256.txt', 'pep-0257.txt', 'pep-0258.txt', 'gpdi.dtd',
                'ppdi.dtd', 'soextblx.dtd', 'dps.cat', 'dps-notes.txt'])
