#!/bin/bash

#- name: make a list of groups
#  shell: |
#      cat /etc/group | cut -d: -f1
#  register: group_names
#  when: 'ansible_distribution != "MacOSX"'

#- name: make a list of groups [mac]
#  shell: dscl localhost -list /Local/Default/Groups
#  register: group_names
#  when: 'ansible_distribution == "MacOSX"'

DISTRO=$1

if [[ $DISTRO == "MacOSX" ]]; then
    dscl localhost -list /Local/Default/Groups
else
    cat /etc/group | cut -d: -f1
fi
