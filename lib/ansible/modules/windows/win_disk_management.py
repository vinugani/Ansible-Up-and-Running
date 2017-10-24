#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2017, Marc Tschapek <marc.tschapek@itelligence.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = r'''
---
module: win_disk_management
version_added: '2.5'
short_description: Select and manage a disk, it's partitions and file systems
description:
   - With the module you can select a disk on the target and manage it (e.g. initializing, partitioning, formatting) with several options.
requirements:
    - Windows 8.1 / Windows 2012R2 (NT 6.3) or newer
author:
    - Marc Tschapek (@marqelme)
options:
  size:
      description:
        - Select disk option.
        - Size of the disk in gigabyte which will be selected.
        - If a size is defined the module will try to select the disk with this passed size.
        - Size value must be equal or greater than 1gb.
  partition_style_select:
      description:
        - Select disk option.
        - Partition style of the disk which will be selected.
      default: raw
      choices:
        - raw
        - mbr
        - gpt
  operational_status:
      description:
        - Select disk option.
        - Operational Status of the disk which will be selected.
      default: offline
      choices:
        - offline
        - online
  read_only:
      description:
        - Select disk option.
        - Read-only status of the disk which will be selected (true=read-only,false=writeable).
      type: bool
      default: 'yes'
  number:
      description:
        - Select disk option.
        - Number of the disk which will be selected.
        - If a number is defined the module will try to select the disk with this passed number.
        - Passed value will be checked in the beginning of the module whether it is an int32 value.
        - If it is of type in64 the module will be canceled.
  partition_style_set:
      description:
        - Manage disk option.
        - Partition style which will be set on selected disk.
      default: gpt
      choices:
        - gpt
        - mbr
  drive_letter:
      description:
        - Manage disk option.
        - Drive letter which will be set for the partition on selected disk.
        - If a drive letter is defined the module will try to set the partition on the selected disk with this passed drive letter.
        - If this drive letter is already in use on the target the module will be canceled.
        - If no drive_letter option value was defined the module will use a free drive letter on the target randomly.
        - If no free drive lettter is left on the target the module will be canceled.
  file_system:
      description:
        - Manage disk option.
        - File system which will be set on selected disk.
        - Maximum volume size for ntfs is 256gb, for refs 1208925819614650gb (1 yobibyte).
        - If the disk size of the selected disk does not match with the passed value for option
          file_system (e.g. "ntfs" over 256000gb) the module will be canceled.
      default: ntfs
      choices:
        - ntfs
        - refs
  label:
      description:
        - Manage disk option.
        - File system label which should be set for the file system on found disk.
      default: ansible_disk
  allocation_unit_size:
      description:
        - Manage disk option.
        - Allocation Unit size which will be set for the file system on selected disk (possible values for file system ntfs 4,8,16,32,64kb;refs 64kb).
        - If option file_system is set to "refs" the allocation unit size will be automatically adjusted to "64" (kb).
      default: 4
      choices:
        - 8
        - 16
        - 32
        - 64
  large_frs:
      description:
        - Manage disk option.
        - Switch to set Large FRS option for file system on selected disk, solely settable for ntfs file system.
        - If this manage disk option was passed to the module it checks whether it is suitable with the passed file_system value.
        - If they do not fit this manage disk options will be automatically disabled.
      type: bool
      default: 'no'
  short_names:
      description:
        - Manage disk option.
        - Switch to set Short Names option for file system on selected disk, solely settable for ntfs file system.
        - If this manage disk option was passed to the module it checks whether it is suitable with the passed file_system value.
        - If they do not fit this manage disk options will be automatically disabled.
      type: bool
      default: 'no'
  integrity_streams:
      description:
        - Manage disk option.
        - Switch to set Integrity Streams option for file system on selected disk, solely settable for refs file system.
        - If this manage disk option was passed to the module it checks whether it is suitable with the passed file_system value.
        - If they do not fit this manage disk options will be automatically disabled.
      type: bool
      default: 'no'
notes:
  - To select the disk and to manage it you have several options which are all described in the documentation.
  - If you pass a decimal value for any of the int options it will be rounded to an even number.
  - To identify the options which are used to select a disk consider the "Select disk option" hint in the option description.
  - To identify the options which are used to manage a disk consider the "Manage disk option" hint in the option description.
  - In order to find only one disk on the target you can use the size and/or number option for the search of the disk.
  - If no size and number option value was defined and multiple disks were found on the target based on the passed option values
    the module will select the first disk found.
  - The module detects any existing volume and/or partition on the selected disk and will cancel the module in this case.
  - If the disk is not yet initialized the module will initialize the disk (set partition style, online and writeable).
  - If the disk is initialized already the script will try to set the disk to "online" and "writeable" (read-only eq. false)
    if it's not the state of the disk already.
  - Further in this case it will convert the partition style of the disk to the selected partition style if needed.
  - The script will stop and start the service "ShellHWService" again in order to avoid disk management GUI messages.
  - If the script fails with an error and the operational status was set from "offline" to "online" before the script will try to set the disk to
    operational status "offline" again but will not be canceled if set "offline" again fails.
  - If the script fails with an error and the writeable status was set from "read-only" to "writeable" before the script will try to set the disk to
    writeable status "read-only" again but will not be canceled if set "read-only" again fails.
  - If you use the --diff option you will get detailed information about the changes on the target.
  - If you use the --check option nothing will be changed on the target but you will get information what would be changed.
'''

EXAMPLES = r'''
- name: Select a defined disk and manage it as specified
  win_disk_management:
    # select_disk_by
    partition_style_select: raw
    operational_status: offline
    read_only: true
    number: 1
    # set_disk_by
    partition_style_set: mbr
    file_system: ntfs
    label: database_disk
    allocation_unit_size: 4
    large_frs: true
    short_names: true
- name: Select a defined disk and manage it as specified
  win_disk_management:
    # select_disk_by
    size: 50
    partition_style_select: mbr
    operational_status: online
    read_only: false
    # set_disk_by
    partition_style_set: gpt
    drive_letter: f
    file_system: refs
    label: application_disk
    allocation_unit_size: 64
    integrity_streams: true
'''

RETURN = r'''
changed:
    description: Whether anything was changed.
    returned: always
    type: boolean
    sample: true
msg:
    description: Possible error message on failure.
    returned: failed
    type: string
    sample: "No free drive_letter left on the target"
change_log:
    description: Dictionary containing all the detailed information about changes on the selected disk.
    returned: always
    type: complex
    contains:
        operational_status:
            description: Detailed information about setting operational status of the disk.
            returned: success or failed
            type: string
            sample: "Disk set online"
        writeable_status:
            description: Detailed information if disk was set from read-only to writeable and if not why it was not set to it.
            returned: success or failed
            type: string
            sample: "Disk set from read-only to writeable"
        initializing:
            description: Detailed information about initializing the disk.
            returned: success or failed
            type: string
            sample: "Disk initialization successful - Partition style raw (partition_style_select) was initalized to gpt (partition_style_set)"
        converting:
            description: Detailed information about converting the partition style of the disk (in case of converting no initalization of disk).
            returned: success or failed
            type: string
            sample: "Partition style mbr (partition_style_select) was converted to gpt (partition_style_set)"
        partitioning:
            description: Detailed information about partition creation on the found disk.
            returned: success or failed
            type: string
            sample: "Initial partition Basic was created successfully on partition style gpt"
        formatting:
            description: Detailed information about volume creation on partitoned disk.
            returned: success or failed
            type: string
            sample: "Volume ReFS was created successfully on partition Basic"
        shellhw_service_state:
            description: Detailed information about executed ShellHWService action (start, stop).
            returned: success or failed
            type: string
            sample: "Could not be set from 'Stopped' to 'Running' again"
'''
