#!/usr/bin/env python

import argparse
import yaml

from jinja2 import Environment, FileSystemLoader

from ansible.playbook import Play
from ansible.playbook.block import Block
from ansible.playbook.role import Role
from ansible.playbook.task import Task

try:
    import argcomplete
except ImportError:
    argcomplete = None

template_file = 'playbooks_keywords.rst.j2'
oblist = {}
clist = []
class_list = [Play, Role, Block, Task]

p = argparse.ArgumentParser(
    description='Generate module documentation from metadata',
)
p.add_argument('--version', action='version', version='%(prog)s 1.0')
p.add_argument("-T", "--template-dir", action="store", dest="template_dir", default="../templates", help="directory containing Jinja2 templates")
p.add_argument("-o", "--output-dir", action="store", dest="output_dir", default='/tmp/', help="Output directory for rst files")
p.add_argument("-d", "--docs-source", action="store", dest="docs", default=None, help="Source for attribute docs")

if argcomplete:
    argcomplete.autocomplete(p, always_complete_options=False, validator=lambda i, k: True)

options = p.parse_args()

for aclass in class_list:
    aobj = aclass()
    name = type(aobj).__name__

    if options.docs:
        with open(options.docs) as f:
            docs = yaml.safe_load(f)
    else:
        docs = {}

    # build ordered list to loop over and dict with attributes
    clist.append(name)
    oblist[name] = dict((x, aobj.__dict__['_attributes'][x]) for x in aobj.__dict__['_attributes'] if 'private' not in x or not x.private)

    # pick up docs if they exist
    for a in oblist[name]:
        if a in docs:
            oblist[name][a] = docs[a]
        else:
            oblist[name][a] = ' UNDOCUMENTED!! '

    # loop is really with_ for users
    if name == 'Task':
        oblist[name]['with_<lookup_plugin>'] = 'with_ is how loops are defined, it can use any available lookup plugin to generate the item list'

    # local_action is implicit with action
    if 'action' in oblist[name]:
        oblist[name]['local_action'] = 'Same as action but also implies ``delegate_to: localhost``'

    # remove unusable (used to be private?)
    for nouse in ('loop', 'loop_args'):
        if nouse in oblist[name]:
            del oblist[name][nouse]

env = Environment(loader=FileSystemLoader(options.template_dir), trim_blocks=True,)
template = env.get_template(template_file)
outputname = options.output_dir + template_file.replace('.j2', '')
tempvars = {'oblist': oblist, 'clist': clist}

with open(outputname, 'w') as f:
    f.write(template.render(tempvars))
