#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2012 Tetsuo Kiso. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
# https://github.com/tetsuok/cabocha-to-tikz-deptree/blob/master/LICENSE

import optparse, os, sys, re, six

class Error(Exception):
  pass

class FormatError(Error):
  pass

class Segment(object):

  def __init__(self):
    self.morphs = []
    self.id = None
    self.head = None

  def is_root(self):
    return self.head == '-1'

  def add(self, m):
    self.morphs.append(m)

  def to_pred(self, case, morphr, predTargs):
    caseID = re.findall(r'({0}\"[0-9]\")'.format(case), morphr)
    if caseID not in predTargs:
        return str(caseID)[2:-2]

  def to_str(self):
    return ''.join([re.split(r'\t', m)[0] for m in self.morphs])

  def to_pas(self):
    bunsetsu, predTargs, morphMerge = [], [], []
    predMerge, targID = '', ''
    count = 0
    for m in self.morphs:
            bunsetsu.append(re.split(r'\t', m, 1))
    for morph in reversed(bunsetsu):
        if 'ID' in morph[-1]:
            targID = re.findall(r'ID\=\"([0-9])\"', morph[-1])
            targID = str(targID)[2:-2]
        if 'type="pred"' in morph[-1]:
            if 'pred' not in predTargs:
                predTargs.append('pred')
                for i in ['ga=', 'o=', 'ni=']:
                    if i in morph[-1]:
                        predTargs.append(self.to_pred(i, morph[-1], predTargs))
            predMerge = ' '.join(predTargs)
    while count < len(bunsetsu):
        for m in bunsetsu:
              morphMerge.append(m[0])
              count += 1
    if morphMerge and (targID or predMerge):
        return ''.join(morphMerge), targID, predMerge
    else:
        return ''.join(morphMerge), None, None

def sentence_to_deptext(sent):
  return ' \& '.join([seg.to_str() for seg in sent]) + ' \\\\'

def getID(case, cval):
  id = re.findall(r'{0}\=\"([0-9])\"'.format(case), cval)
  return str(id)[2:-2]

def convID(pLst, id):
      return str(pLst.index(id) + 1)

def sentence_to_pas(sent):
  pLst = []
  pD, aD = {}, {}
  for seg in sent:
     if seg.to_pas() != None:
         temp, argID, targs = seg.to_pas()
         if temp:
             pLst.append(temp)
             if argID:
                 aD[argID] = temp
             if targs:
                 pD[temp] = targs
  joined = ' \& '.join(pLst) + ' \\\\' + '\n'
  return (joined), (pas_edges(pD, aD, pLst))

def pas_edges(pD, aD, pLst):
  cD = {'ga': ('red', 'NOM'), 'o': ('cyan, dashed', 'ACC'), 'ni': ('teal', 'DAT')}
  edges = ["\n"]
  soffset = 0
  eoffset = 0
  for (i, t) in six.iteritems(pD):
        for (k, (c, l)) in six.iteritems(cD):
           for j in t.split(' '):
               if k in j:
                   sid = aD.get(getID(k, j))
                   if sid in pLst and i in pLst:
                       cid = convID(pLst, sid)
                       pid = convID(pLst, i)
                       if cid != pid:
                           if any(pid in edge[-12:-8] for edge in edges if len(edge) > 1):
                               if int(pid) - int(cid) > 1:
                                   if soffset >= 0:
                                       soffset += 5
                                   else:
                                       soffset = 5
                               else:
                                   soffset -= 5
                           if any(cid in edge[-9:-5] for edge in edges if len(edge) > 1):
                               eoffset -= 5
                           edges.append('\n\depedge[style={%s}, edge start x offset=%spt, edge end x offset=%spt, edge below, label style={rounded corners=0, draw=black, top color=cyan, bottom color=cyan, text=black, below}]{%s}{%s}{%s}' % (c, str(soffset), str(eoffset), pid, cid, l))
  ej = ''.join(edges)
  if ej != None:
    return ej

def wrap_depedge(h, m, offset):
    return '\depedge[edge style={black}, edge end x offset=%s]{%d}{%d}{}' % (offset, int(h)+1, int(m)+1)

def wrap_depedges(sent):
    depedges = []
    offset = 0
    for seg in sent:
        if len(depedges) > 0:
            if any(str(int(seg.head)+1) in edge[-5:] for edge in depedges):
                offset -= 5
        if not seg.is_root():
            depedges.append(wrap_depedge(seg.id, seg.head, str(offset)))
    return '\n'.join(depedges)

def read_deptree(f):
  sentences = []
  sent = []
  segment = Segment()
  for l in f:
    if l.startswith('EOS'):
      sent.append(segment)
      sentences.append(sent)
      segment = Segment()
      sent = []
    elif l.startswith('*'):
      if segment.id is not None:
        sent.append(segment)
      segment = Segment()
      lis = l.rstrip().split(' ')
      if len(lis) != 5:
        raise FormatError('Illegal format:' + l)
      segment.id = lis[1]
      if lis[2][-1].isalpha():
        segment.head = lis[2][:-1]
      else:
        raise FormatError('Illegal format:' + l)
    else:
      segment.add(l.rstrip())
  return sentences

class LaTeXFormatter(object):

    def __init__(self, doc_opt, font, tikz_dep_opt, tikz_deptxt_opt):
        self.doc_opt = doc_opt
        self.font = font
        self.tikz_dep_opt = tikz_dep_opt
        self.tikz_deptxt_opt = tikz_deptxt_opt

    def latex_header(self):
        return r'''\documentclass[convert=true]{%s}
\usepackage{tikz-dependency}
\usepackage{zxjatype}
\setjamainfont[Scale=1]{%s}
\begin{document}
''' % (self.doc_opt, self.font)

    def latex_footer(self):
        return '''\end{document}'''

    def print_tikz_dep(self, sent):
        joined, edges = sentence_to_pas(sent)
        return (r'''\begin{dependency}[%s, text only label, edge vertical padding=1]
\begin{deptext}[%s, column sep=0.1cm, nodes={draw=black, inner sep=1ex, text=black}]
%s
\end{deptext}
%s%s
\end{dependency}
''' % (self.tikz_dep_opt, self.tikz_deptxt_opt, sentence_to_deptext(sent).replace('%', '\%'), wrap_depedges(sent), edges))

def set_default_font():
  '''Set up default font according to major platforms
  (Windows, Mac OS X, Linux).
  '''
  if os.name == 'nt':
    return 'Noto Sans Japanese Regular' # メイリオ
  elif os.name == 'posix' and os.uname()[0] == 'Darwin':
    return 'Hiragino Kaku Gothic Pro W3'
  elif os.name == 'posix' and os.uname()[0] == 'Linux':
    return 'IPAPGothic'
  else:
    return 'IPAPGothic'

def parse_options():
  default_font = set_default_font()
  parser = optparse.OptionParser(usage='%prog [options] data')

  parser.add_option('--doc-option', dest='doc_opt', default='standalone',
                    help='the options of documentclass')
  parser.add_option('--font', dest='font', default=default_font,
                    help='Japanese font')
  parser.add_option('--dep-option', dest='dep_opt', default='theme=simple',
                    help='the option of the dependency environment')
  parser.add_option('--deptxt-option', dest='deptxt_opt', default='column sep=1em',
                    help='the option of the deptext environment')
  (options, unused_args) = parser.parse_args()
  return (options, unused_args)

def main():
  opts, unused_args = parse_options()
  tex_formatter = LaTeXFormatter(opts.doc_opt, opts.font, opts.dep_opt, opts.deptxt_opt)

  if len(unused_args) == 0:
    sents = read_deptree(sys.stdin)
  else:
    with open(unused_args[0], encoding="utf8") as f:
      sents = read_deptree(f)

  with open(unused_args[1], "w", encoding="utf8") as out_d:
      for sent in sents:
        out_d.write(tex_formatter.latex_header() + tex_formatter.print_tikz_dep(sent) +
        tex_formatter.latex_footer())

if __name__ == '__main__':
  main()
