"""
Yet Another Python Templating Utility (YAPTU) release 2.0 (2001/06/13)
    by Alex Martelli, with David Goodger, and input by Mario Ruggier.

We often need to copy some "template" text (normally read from an input file),
expanding Python expressions embedded in it, and often also executing embedded
Python statements, particularly for selection or repetition.  Yaptu is a small
but complete module for this job, suitable for most kind of structured-text
input -- it lets client-code decide which regular-expressions denote embedded
Python expressions and statements, so the re's can be selected to fit in most
any kind of structured text.  See also xYaptu, by Mario Ruggier and Alex
Martelli, for a Yaptu subclass tailored specifically to XML needs.

Theory of operations: the (compiled) re that identifies expressions is used for
a .sub() on each "normal" line of input -- for each match, .group(1) is
evaluated as a Python expression (in specified namespaces), and the result
passed to str() and substituted.  Many non-overlapping matches per line are OK;
results are not re-scanned.  Expressions (and statements) may be preprocessed
by passing an optional callable -- if given, it's called with the expression or
statement as first arg, 'eval' or 'exec' as second, and must return a string
or code-object suitable for eval or exec respectively.  Exceptions raised in
expressions (only) may be handled by passing an optional callable -- if given,
it's called in an except: clause with the expression as only argument (the
default is to re-raise the expression, terminating Yaptu and propagating).

Statement embedding uses 5 more optional re's.  One identifies simple (i.e.,
single-line) statements.  Another identifies physical lines that continue a
previous Python logical line (such continuations can be used for all kinds of
embedded statements).  Three more re's identify: (1) the leading clause in a
compound statement; (2) a continuation clause in a compound statement (usually
an else or elif); (3) the end of a compound statement.  Each of these 5 re's is
used in a .match() [i.e., must match from line-start].  Python comments are
allowed, but not required, for each kind of Python _physical_ line (beware
comments at the end of a _logical_ line which is not the end of its _physical_
line!).  Yaptu imposes no limit to the nesting of compound statements.

See the next string in the source for more on how Yaptu works, and the
example code at the end for a typical use.
"""

"""
Net of comments, whitespace, docstrings, and test code, YAPTU is just 84 [TODO:
recount!] source-lines of code, but a lot happens within that small compass.
An instance of the '_NeverMatch' auxiliary class is the default for optional
parameter re's -- its polymorphism with compiled-re objects (regarding the only
two methods of the latter that Yaptu uses, .sub and .match) saves tests in the
main body of code, and simplifies it -- a good general idiom to keep in mind.

An instance of Yaptu's 'copier' class has a certain amount of state, besides
the relevant compiled-re's (or _Nevermatch instance), and holds it in two
dictionary attributes -- self.globals, the dictionary that was originally
passed in for expression-substitution, and self.locals, another dictionary
which is used as the local-namespace for all of Yaptu's exec and eval uses.
Two internal-use-only items in self.locals, in particular (with names starting
with '_') indicate the block of template-text being 'copied' (a sequence of
lines, each ending in a '\n'), as '_block', and the bound-method that performs
the copying, self._copyblock, as '_copyblock'.  Holding these two pieces of state
in self.locals is not quaint personal usage -- it's part of the key to Yaptu's
workings, since self.locals is what is guaranteed to be made available to the
code that Yaptu exec's (self.globals, too, but Yaptu does NOT mess with THAT
dictionary -- it belongs to its caller!). Since .copyblock must be recursive
(the simplest way to ensure no nesting limitations), it is important that nested
recursive calls be always able to further recurse, if needed, through their
exec statements.  Access to _block is similarly necessary -- ._copyblock only
takes as arguments the line *indices* inside _block that a given recursive
call is processing (in the usual form -- index of first line to process,
index of first following line to AVOID processing; i.e., lower-bound-included,
upper-bound-excluded, as everywhere in Python).

Copier._copyblock is the heart of YAPTU. The repl nested function ie passed to
the .sub method of compiled RE objects to get the text to use for each
expression substitution -- it uses eval on the expression string, and str() on
the result to ensure it's turned back into a string.  Substitution is only
performed on normal lines -- those that are not recognized as statements or
parts of statements.  copyblock's while loop examines lines up to the end
of the block.  If it matches a compound-start, it delegates to the relevant
method; else, if it matches a simple-statement, it delegates to that method;
otherwise, it performs substitutions if needed, then copies the resulting line
to the list of result lines.
The method that handles simple statements basically just execs them.
The method that handles compound statements is a tad more refined.  It
uses a while loop looking for compound-clause and compound-end while
keeping track of nesting level; meanwhiles it builds up a code string, where
each clause is followed (on an indented newline) by a recursive call to
_copyblock(start, end) for suitable start and end.  When done, the code
string is exec'd.  This will inevitably invoke _copyblock recursively,
but that doesn't disturb the latter loop's state, as it's based on
local variables 'current' and 'blocklast' -- nothing special is needed
to ensure that, it's part of normal recursive-invocation mechanisms.


Main contributions by David Goodger to the original Yaptu as coded
by Alex Martelli (part of the Alex's coded functionality being based
in turn on input by Mario Ruggier as the latter wrote xYaptu):
    more readable (shorter methods, longer variable names,
        compound statements never on the same line)
    split recognition of embedded statements into several
        separate re's, eliminating previous comment-trickery,
        and added statement-continuation pattern
    partly reformed input and output and convinced Alex that
        having blocks of lines as I _and_ O was best (no files)
    condign editing to docstrings, comments, test-code

Alex revised it all over again after that and carries responsibility
for bugs that may still be there -- mailto:aleaxit@yahoo.com
"""

import sys


# utility stuff to avoid tests in the mainline code
class _NeverMatch:
    """Polymorphic with a regex that never matches"""
    def match(self, line):
        return None
    def sub(self, repl, line):
        return line
_never = _NeverMatch()                  # one reusable instance suffices
def _identity(string, why):
    """A do-nothing-special-to-the-input, just-return-it function."""
    return string
def _nohandle(string):
    """A do-nothing exception handler that just re-raises the exception."""
    raise
# other utility stuff
def _extract(match):
    return match.string[match.end(0):].lstrip()

class Copier:
    """Smart-copier (YAPTU) class. copy() is the entry point."""
    def __init__(self, expression=_never, globalsdict={}, statement=_never,
                 continuation=_never, compound_start=_never,
                 compound_clause=_never, compound_end=_never,
                 preprocess=_identity, handle=_nohandle):
        """Initialize self's attributes"""
        self.expression = expression
        self.globals = globalsdict
        self.locals = {'_copyblock': self._copyblock}
        self.statement = statement
        self.continuation = continuation
        self.compound_start = compound_start
        self.compound_clause = compound_clause
        self.compound_end = compound_end
        self.preprocess = preprocess
        self.handle = handle

    def copy(self, inputlines):
        """Process a list of template lines, return a list of result lines."""
        self.locals['_block'] = inputlines
        self.results = []
        self._copyblock(0, len(inputlines))
        return self.results

    def _repl(self, match):
        """Evaluate and return the expression found, for replacement."""
        # for debugging, uncomment:
        ##print '!!! replacing', match.group(1)
        expression = self.preprocess(match.group(1), 'eval')
        try:
            return str(eval(expression, self.globals, self.locals))
        except:
            return str(self.handle(expression))
        
    def _copyblock(self, current, last):
        """Main copy method: process lines [current,last) of block"""
        block = self.locals['_block']
        while current < last:
            line = block[current]
            # for debugging, uncomment:
            ##print '-> line %s: "%s"' % (current, line.rstrip())
            match = self.compound_start.match(line)
            if match:
                current = self._compound_statement(match, current, last)
            else:
                match = self.statement.match(line)
                if match:
                    current = self._simple_statement(match, current, last)
                else:               # normal line, just copy with substitution
                    self.results.append(self.expression.sub(self._repl, line))
                    # for debugging, uncomment:
                    ##print '-> new line: "%s"' % self.results[-1].rstrip()
            current += 1

    def _simple_statement(self, match, current, last):
        """Isolate and execute a simple statement. Return last line index."""
        codelines, current = self._continue(_extract(match), current + 1, last)
        code = self.preprocess(''.join(codelines), 'exec')
        # for debugging, uncomment:
        ##print '-> Executing statement:', code
        exec code in self.globals, self.locals
        return current

    def _compound_statement(self, match, current, last):
        """Isolate and execute a compound statement. Return last line index."""
        # for debugging, uncomment:
        ##print '-> matched compound start'
        codelines, current = self._continue(_extract(match), current + 1, last)
        blocklast = current + 1 # look for block end from here on
        nest = 1                # count nesting levels of statements
        block = self.locals['_block']
        while blocklast < last:
            line = block[blocklast]
            # for debugging, uncomment:
            ##print ('%s-> line %s: "%s"'
            ##       % ('--' * nest, blocklast, line.rstrip()))
            # first look for nested statements or 'finish' lines
            if self.compound_end.match(line): # found a statement-end
                # for debugging, uncomment:
                ##print '%s-> matched compound end' % ('--' * nest)
                nest = nest - 1 # update (decrease) nesting
                if nest == 0:
                    break
            elif self.compound_start.match(line): # found a nested statement
                nest += 1       # update (increase) nesting
                # for debugging, uncomment:
                ##print '%s-> matched compound start' % ('--' * nest)
            elif nest == 1:     # look for compound clause only at this nesting
                match = self.compound_clause.match(line)
                if match:       # found a contin.-statement
                    # for debugging, uncomment:
                    ##print '---> matched compound clause'
                    clauselines, contend = self._continue(_extract(match), blocklast + 1, last)
                    # recursive copyblock on suite just ended:
                    codelines.append("    _copyblock(%s,%s)\n"%(current+1, blocklast))
                    codelines.extend(clauselines)
                    blocklast = contend
                    current = blocklast
            blocklast += 1
        # recursive copyblock on final suite:
        codelines.append("    _copyblock(%s,%s)\n"%(current+1, blocklast))
        code = self.preprocess(''.join(codelines), 'exec')
        # for debugging, uncomment:
        ##print '-> Executing block: {%s}' % code
        exec code in self.globals, self.locals
        return blocklast

    def _continue(self, first, current, last):
        """Return continuation lines from current on, and last line index."""
        continuation = [first]
        block = self.locals['_block']
        while current < last:
            match = self.continuation.match(block[current])
            if match:
                # for debugging, uncomment:
                ##print '---> matched continuation: "%s"' % match.string
                continuation.append(_extract(match))
                current += 1
            else:
                break
        return continuation, current - 1


if __name__ == '__main__':
    """Test: copy a block of lines, with full processing"""
    import re
    expression = re.compile('`([^`]+)`')
    statement = re.compile('# ')
    continuation = re.compile(r'#\\')
    compound_start = re.compile('#>')
    compound_clause = re.compile('#=')
    compound_end = re.compile('#<')
    def execho(code, why):
        if why=='exec':
            print "->%s:\n%s"%(why, code.rstrip())
        return code
    cop = Copier(expression, {'x':23}, statement, continuation,
                 compound_start, compound_clause, compound_end, execho)
    lines_block = r"""
A first, plain line -- it just gets copied.
A second line, with `x` substitutions.
#  x += 1    # a simple statement
A third line, with `x` substitutions.
#  x += \
#\     1     # a continuation (note backslash above)
A fourth line, with `x` substitutions.
#  x = (x +  # a comment is OK here
#\      1)   # a continuation (note parentheses)
Now the substitutions are `x`.
#> if x>23:  # start of a compound statement
After all, `x` is rather large!
#= else:     # a compound statement clause
After all, `x` is rather small!
#<           # end of a compound statement
#> for i in range(3):
  Also, `i` times `x` is `i*x`.
#<
One last, plain line at the end.""".splitlines(1) # 1 means keep line ends
    print '*** input:'
    print ''.join(lines_block)
    print
    # for debugging, uncomment:
    ##print '\n*** processing:'
    results = cop.copy(lines_block)
    print '\n*** output:'
    print ''.join(results)

