#! /usr/bin/env python
# $Id: templater.py,v 1.2 2001/08/04 15:07:26 goodger Exp $

import os, sys, time, re, getopt
#from htmlesc import htmlesc
import yaptu
from dps.statemachine import StateMachine, State, string2lines


class ScanState(State):

    patterns = {'overline': re.compile('=+$'),
                'rfc822': re.compile('([^ :]+): '),
                'blank': re.compile('\s*$')}
    initialtransitions = ['overline', 'rfc822', 'blank']
    blankarmed = 0

    def overline(self, match, context, nextstate):
        title = self.statemachine.nextline() # get title
        self.statemachine.nextline()    # skip underline
        return context, nextstate, [('title', title.strip())]

    def rfc822(self, match, context, nextstate):
        self.blankarmed = 1
        return context, nextstate, [(match.group(1).strip(),
                                     match.string[match.end():].strip())]

    def blank(self, match, context, nextstate):
        if self.blankarmed:
            raise EOFError
        else:
            return context, nextstate, []


def scanfile(path, file):
    ##print >>sys.stderr, 'path=%s, file=%s' % (path, file)
    filename = os.path.normpath(os.path.join(path, file))
    inputlines = string2lines(open(filename).read())
    sm = StateMachine([ScanState], initialstate='ScanState')
    results = sm.run(inputlines)
    fields = {}
    for key, value in results:
        fields[key.lower()] = value
    ##print >>sys.stderr, 'raw fields=%s' % fields
    info = []
    if fields.has_key('created') and not fields.has_key('date'):
        fields['date'] = fields['created']
    if fields.has_key('last-modified'):
        fields['date'] = fields['last-modified']
    if fields.has_key('date'):
        if fields['date'][:6] == '$Date:':
            fields['date'] = fields['date'][7:17].replace('/', '-')
        info.append('Date: %s.' % fields['date'])
    if fields.has_key('version'):
        if fields['version'][:10] == '$Revision:':
            version = fields['version'][11:-2]
        else:
            version = fields['version']
        info.append('Version: %s.' % version)
    elif 0 and fields.has_key('revision'):
        if fields['revision'][:10] == '$Revision:':
            revision = fields['revision'][11:-2]
        else:
            revision = fields['revision']
        info.append('Revision: %s.' % revision)
    if fields.has_key('status'):
        info.append('Status: %s.' % fields['status'])
    if fields.has_key('pep'):
        fields['title'] = 'PEP %(pep)s: %(title)s' % fields
    ##print >>sys.stderr, 'post-processing fields=%s' % fields
    return fields, ' '.join(info)

def templater(templatelines, path, files):
    dict = {'path': path, 'files': files, 'date': time.strftime('%Y-%m-%d'),
            'scanfile': scanfile}
    expression = re.compile('`([^`]+)`')
    statement = re.compile('# ')
    continuation = re.compile(r'#\\')
    compound_start = re.compile('#>')
    compound_clause = re.compile('#=')
    compound_end = re.compile('#<')
    copier = yaptu.Copier(expression, dict, statement, continuation,
                          compound_start, compound_clause, compound_end)
    output = copier.copy(templatelines)
    return output

def main(template, path, files):
    templatetext = open(template).read()
    templatetext = templatetext.replace("\r\n", "\n").replace("\r", "\n")
    templatelines = templatetext.splitlines(1)
    output = templater(templatelines, path, files)
    outputname = template[:template.rfind('.')]
    outputfile = open(outputname, 'w')
    outputfile.writelines(output)
    outputfile.close

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
