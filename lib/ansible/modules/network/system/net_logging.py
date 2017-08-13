#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2017, Ansible by Red Hat, inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'core'}


DOCUMENTATION = """
---
module: net_logging
version_added: "2.4"
author: "Ganesh Nalawade (@ganeshrn)"
short_description: Manage logging on network devices
description:
  - This module provides declarative management of logging
    on network devices.
options:
  dest:
    description:
      - Destination of the logs.
    choices: ['console', 'host']
  name:
    description:
      - If value of C(dest) is I(host) it indicates file-name
        the host name to be notified.
  facility:
    description:
      - Set logging facility.
  level:
    description:
      - Set logging severity levels.
  aggregate:
    description: List of logging definitions.
  purge:
    description:
      - Purge logging not defined in the aggregates parameter.
    default: no
  state:
    description:
      - State of the logging configuration.
    default: present
    choices: ['present', 'absent']
"""

EXAMPLES = """
- name: configure console logging
  net_logging:
    dest: console
    facility: any
    level: critical

- name: remove console logging configuration
  net_logging:
    dest: console
    state: absent

- name: configure host logging
  net_logging:
    dest: host
    name: 1.1.1.1
    facility: kernel
    level: critical
- name: Add logging aggregate
  net_logging:
    aggregate:
      - { dest: file, name: test1, facility: all, level: info }
      - { dest: file, name: test2, facility: news, level: debug }
- name: Remove logging aggregate
  net_logging:
    aggregate:
      - { dest: console, facility: all, level: info, state: absent }
      - { dest: console, facility: daemon, level: warning, state: absent }
      - { dest: file, name: test2, facility: news, level: debug, state: absent }
"""

RETURN = """
commands:
  description: The list of configuration mode commands to send to the device
  returned: always, except for the platforms that use Netconf transport to manage the device.
  type: list
  sample:
    - logging console critical
"""
