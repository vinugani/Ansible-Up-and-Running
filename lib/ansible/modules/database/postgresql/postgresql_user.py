#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['stableinterface'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: postgresql_user
short_description: Adds or removes a users (roles) from a PostgreSQL database.
description:
   - Add or remove PostgreSQL users (roles) from a remote host and, optionally,
     grant the users access to an existing database or tables.
   - The fundamental function of the module is to create, or delete, roles from
     a PostgreSQL cluster. Privilege assignment, or removal, is an optional
     step, which works on one database at a time. This allows for the module to
     be called several times in the same module to modify the permissions on
     different databases, or to grant permissions to already existing users.
   - A user cannot be removed until all the privileges have been stripped from
     the user. In such situation, if the module tries to remove the user it
     will fail. To avoid this from happening the fail_on_user option signals
     the module to try to remove the user, but if not possible keep going; the
     module will report if changes happened and separately if the user was
     removed or not.
version_added: "0.6"
options:
  name:
    description:
      - name of the user (role) to add or remove
    required: true
    default: null
  password:
    description:
      - set the user's password, before 1.4 this was required.
      - >
        When passing an encrypted password, the encrypted parameter must also be true, and it must be generated with the format
        C('str[\\"md5\\"] + md5[ password + username ]'), resulting in a total of 35 characters.  An easy way to do this is:
        C(echo \\"md5`echo -n \\"verysecretpasswordJOE\\" | md5`\\"). Note that if the provided password string is already in
        MD5-hashed format, then it is used as-is, regardless of encrypted parameter.
    required: false
    default: null
  db:
    description:
      - name of database where permissions will be granted
    required: false
    default: null
  fail_on_user:
    description:
      - if C(yes), fail when user can't be removed. Otherwise just log and continue
    required: false
    default: 'yes'
    choices: [ "yes", "no" ]
  port:
    description:
      - Database port to connect to.
    required: false
    default: 5432
  login_user:
    description:
      - User (role) used to authenticate with PostgreSQL
    required: false
    default: postgres
  login_password:
    description:
      - Password used to authenticate with PostgreSQL
    required: false
    default: null
  login_host:
    description:
      - Host running PostgreSQL.
    required: false
    default: localhost
  login_unix_socket:
    description:
      - Path to a Unix domain socket for local connections
    required: false
    default: null
  priv:
    description:
      - "PostgreSQL privileges string in the format: C(table:priv1,priv2)"
    required: false
    default: null
  role_attr_flags:
    description:
      - "PostgreSQL role attributes string in the format: CREATEDB,CREATEROLE,SUPERUSER"
    required: false
    default: ""
    choices: [ "[NO]SUPERUSER","[NO]CREATEROLE", "[NO]CREATEUSER", "[NO]CREATEDB",
                    "[NO]INHERIT", "[NO]LOGIN", "[NO]REPLICATION", "[NO]BYPASSRLS" ]
  state:
    description:
      - The user (role) state
    required: false
    default: present
    choices: [ "present", "absent" ]
  encrypted:
    description:
      - whether the password is stored hashed in the database. boolean. Passwords can be passed already hashed or unhashed, and postgresql ensures the
        stored password is hashed when encrypted is set.
    required: false
    default: false
    version_added: '1.4'
  expires:
    description:
      - sets the user's password expiration.
    required: false
    default: null
    version_added: '1.4'
  no_password_changes:
    description:
      - if C(yes), don't inspect database for password changes. Effective when C(pg_authid) is not accessible (such as AWS RDS). Otherwise, make
        password changes as necessary.
    required: false
    default: 'no'
    choices: [ "yes", "no" ]
    version_added: '2.0'
  ssl_mode:
    description:
      - Determines whether or with what priority a secure SSL TCP/IP connection will be negotiated with the server.
      - See https://www.postgresql.org/docs/current/static/libpq-ssl.html for more information on the modes.
      - Default of C(prefer) matches libpq default.
    required: false
    default: prefer
    choices: [disable, allow, prefer, require, verify-ca, verify-full]
    version_added: '2.3'
  ssl_rootcert:
    description:
      - Specifies the name of a file containing SSL certificate authority (CA) certificate(s). If the file exists, the server's certificate will be
        verified to be signed by one of these authorities.
    required: false
    default: null
    version_added: '2.3'
notes:
   - The default authentication assumes that you are either logging in as or
     sudo'ing to the postgres account on the host.
   - This module uses psycopg2, a Python PostgreSQL database adapter. You must
     ensure that psycopg2 is installed on the host before using this module. If
     the remote host is the PostgreSQL server (which is the default case), then
     PostgreSQL must also be installed on the remote host. For Ubuntu-based
     systems, install the postgresql, libpq-dev, and python-psycopg2 packages
     on the remote host before using this module.
   - If the passlib library is installed, then passwords that are encrypted
     in the DB but not encrypted when passed as arguments can be checked for
     changes. If the passlib library is not installed, unencrypted passwords
     stored in the DB encrypted will be assumed to have changed.
   - If you specify PUBLIC as the user, then the privilege changes will apply
     to all users. You may not specify password or role_attr_flags when the
     PUBLIC user is specified.
   - The ssl_rootcert parameter requires at least Postgres version 8.4 and I(psycopg2) version 2.4.3.
requirements: [ psycopg2 ]
author: "Ansible Core Team"
'''

EXAMPLES = '''
# Create django user and grant access to database and products table
- postgresql_user:
    db: acme
    name: django
    password: ceec4eif7ya
    priv: "CONNECT/products:ALL"

# Create rails user, grant privilege to create other databases and demote rails from super user status
- postgresql_user:
    name: rails
    password: secret
    role_attr_flags: CREATEDB,NOSUPERUSER

# Remove test user privileges from acme
- postgresql_user:
    db: acme
    name: test
    priv: "ALL/products:ALL"
    state: absent
    fail_on_user: no

# Remove test user from test database and the cluster
- postgresql_user:
    db: test
    name: test
    priv: ALL
    state: absent

# Example privileges string format
# INSERT,UPDATE/table:SELECT/anothertable:ALL

# Remove an existing user's password
- postgresql_user:
    db: test
    user: test
    password: NULL
'''

import itertools
import re
import traceback
from distutils.version import StrictVersion
from hashlib import md5

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    postgresqldb_found = False
else:
    postgresqldb_found = True

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.database import pg_quote_identifier, SQLParseError
from ansible.module_utils._text import to_bytes, to_native
from ansible.module_utils.six import iteritems


FLAGS = ('SUPERUSER', 'CREATEROLE', 'CREATEUSER', 'CREATEDB', 'INHERIT', 'LOGIN', 'REPLICATION')
FLAGS_BY_VERSION = {'BYPASSRLS': '9.5.0'}

VALID_PRIVS = dict(table=frozenset(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER', 'ALL')),
                   database=frozenset(
                       ('CREATE', 'CONNECT', 'TEMPORARY', 'TEMP', 'ALL')),
                   )

# map to cope with idiosyncracies of SUPERUSER and LOGIN
PRIV_TO_AUTHID_COLUMN = dict(SUPERUSER='rolsuper', CREATEROLE='rolcreaterole',
                             CREATEUSER='rolcreateuser', CREATEDB='rolcreatedb',
                             INHERIT='rolinherit', LOGIN='rolcanlogin',
                             REPLICATION='rolreplication', BYPASSRLS='rolbypassrls')


class InvalidFlagsError(Exception):
    pass


class InvalidPrivsError(Exception):
    pass

# ===========================================
# PostgreSQL module specific support methods.
#


def user_exists(cursor, user):
    # The PUBLIC user is a special case that is always there
    if user == 'PUBLIC':
        return True
    query = "SELECT rolname FROM pg_roles WHERE rolname=%(user)s"
    cursor.execute(query, {'user': user})
    return cursor.rowcount > 0


def user_add(cursor, user, password, role_attr_flags, encrypted, expires):
    """Create a new database user (role)."""
    # Note: role_attr_flags escaped by parse_role_attrs and encrypted is a
    # literal
    query_password_data = dict(password=password, expires=expires)
    query = ['CREATE USER %(user)s' %
             {"user": pg_quote_identifier(user, 'role')}]
    if password is not None:
        query.append("WITH %(crypt)s" % {"crypt": encrypted})
        query.append("PASSWORD %(password)s")
    if expires is not None:
        query.append("VALID UNTIL %(expires)s")
    query.append(role_attr_flags)
    query = ' '.join(query)
    cursor.execute(query, query_password_data)
    return True


def user_should_we_change_password(current_role_attrs, user, password, encrypted):
    """Check if we should change the user's password.

    Compare the proposed password with the existing one, comparing
    hashes if encrypted. If we can't access it assume yes.
    """

    if current_role_attrs is None:
        # on some databases, E.g. AWS RDS instances, there is no access to
        # the pg_authid relation to check the pre-existing password, so we
        # just assume password is different
        return True

    # Do we actually need to do anything?
    pwchanging = False
    if password is not None:
        # 32: MD5 hashes are represented as a sequence of 32 hexadecimal digits
        #  3: The size of the 'md5' prefix
        # When the provided password looks like a MD5-hash, value of
        # 'encrypted' is ignored.
        if ((password.startswith('md5') and len(password) == 32 + 3) or encrypted == 'UNENCRYPTED'):
            if password != current_role_attrs['rolpassword']:
                pwchanging = True
        elif encrypted == 'ENCRYPTED':
            hashed_password = 'md5{0}'.format(md5(to_bytes(password) + to_bytes(user)).hexdigest())
            if hashed_password != current_role_attrs['rolpassword']:
                pwchanging = True

    return pwchanging


def user_alter(db_connection, module, user, password, role_attr_flags, encrypted, expires, no_password_changes):
    """Change user password and/or attributes. Return True if changed, False otherwise."""
    changed = False

    cursor = db_connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Note: role_attr_flags escaped by parse_role_attrs and encrypted is a
    # literal
    if user == 'PUBLIC':
        if password is not None:
            module.fail_json(msg="cannot change the password for PUBLIC user")
        elif role_attr_flags != '':
            module.fail_json(msg="cannot change the role_attr_flags for PUBLIC user")
        else:
            return False

    # Handle passwords.
    if not no_password_changes and (password is not None or role_attr_flags != '' or expires is not None):
        # Select password and all flag-like columns in order to verify changes.
        try:
            select = "SELECT * FROM pg_authid where rolname=%(user)s"
            cursor.execute(select, {"user": user})
            # Grab current role attributes.
            current_role_attrs = cursor.fetchone()
        except psycopg2.ProgrammingError:
            current_role_attrs = None
            db_connection.rollback()

        pwchanging = user_should_we_change_password(current_role_attrs, user, password, encrypted)

        role_attr_flags_changing = False
        if role_attr_flags:
            role_attr_flags_dict = {}
            for r in role_attr_flags.split(' '):
                if r.startswith('NO'):
                    role_attr_flags_dict[r.replace('NO', '', 1)] = False
                else:
                    role_attr_flags_dict[r] = True

            for role_attr_name, role_attr_value in role_attr_flags_dict.items():
                if current_role_attrs[PRIV_TO_AUTHID_COLUMN[role_attr_name]] != role_attr_value:
                    role_attr_flags_changing = True

        if expires is not None:
            cursor.execute("SELECT %s::timestamptz;", (expires,))
            expires_with_tz = cursor.fetchone()[0]
            expires_changing = expires_with_tz != current_role_attrs.get('rolvaliduntil')
        else:
            expires_changing = False

        if not pwchanging and not role_attr_flags_changing and not expires_changing:
            return False

        alter = ['ALTER USER %(user)s' % {"user": pg_quote_identifier(user, 'role')}]
        if pwchanging:
            alter.append("WITH %(crypt)s" % {"crypt": encrypted})
            alter.append("PASSWORD %(password)s")
            alter.append(role_attr_flags)
        elif role_attr_flags:
            alter.append('WITH %s' % role_attr_flags)
        if expires is not None:
            alter.append("VALID UNTIL %(expires)s")

        query_password_data = dict(password=password, expires=expires)
        try:
            cursor.execute(' '.join(alter), query_password_data)
            changed = True
        except psycopg2.InternalError as e:
            if e.pgcode == '25006':
                # Handle errors due to read-only transactions indicated by pgcode 25006
                # ERROR:  cannot execute ALTER ROLE in a read-only transaction
                changed = False
                module.fail_json(msg=e.pgerror, exception=traceback.format_exc())
                return changed
            else:
                raise psycopg2.InternalError(e)

    elif no_password_changes and role_attr_flags != '':
        # Grab role information from pg_roles instead of pg_authid
        select = "SELECT * FROM pg_roles where rolname=%(user)s"
        cursor.execute(select, {"user": user})
        # Grab current role attributes.
        current_role_attrs = cursor.fetchone()

        role_attr_flags_changing = False

        if role_attr_flags:
            role_attr_flags_dict = {}
            for r in role_attr_flags.split(' '):
                if r.startswith('NO'):
                    role_attr_flags_dict[r.replace('NO', '', 1)] = False
                else:
                    role_attr_flags_dict[r] = True

            for role_attr_name, role_attr_value in role_attr_flags_dict.items():
                if current_role_attrs[PRIV_TO_AUTHID_COLUMN[role_attr_name]] != role_attr_value:
                    role_attr_flags_changing = True

        if not role_attr_flags_changing:
            return False

        alter = ['ALTER USER %(user)s' %
                 {"user": pg_quote_identifier(user, 'role')}]
        if role_attr_flags:
            alter.append('WITH %s' % role_attr_flags)

        try:
            cursor.execute(' '.join(alter))
        except psycopg2.InternalError as e:
            if e.pgcode == '25006':
                # Handle errors due to read-only transactions indicated by pgcode 25006
                # ERROR:  cannot execute ALTER ROLE in a read-only transaction
                changed = False
                module.fail_json(msg=e.pgerror, exception=traceback.format_exc())
                return changed
            else:
                raise psycopg2.InternalError(e)

        # Grab new role attributes.
        cursor.execute(select, {"user": user})
        new_role_attrs = cursor.fetchone()

        # Detect any differences between current_ and new_role_attrs.
        changed = current_role_attrs != new_role_attrs

    return changed


def user_delete(cursor, user):
    """Try to remove a user. Returns True if successful otherwise False"""
    cursor.execute("SAVEPOINT ansible_pgsql_user_delete")
    try:
        cursor.execute("DROP USER %s" % pg_quote_identifier(user, 'role'))
    except:
        cursor.execute("ROLLBACK TO SAVEPOINT ansible_pgsql_user_delete")
        cursor.execute("RELEASE SAVEPOINT ansible_pgsql_user_delete")
        return False

    cursor.execute("RELEASE SAVEPOINT ansible_pgsql_user_delete")
    return True


def has_table_privileges(cursor, user, table, privs):
    """
    Return the difference between the privileges that a user already has and
    the privileges that they desire to have.

    :returns: tuple of:
        * privileges that they have and were requested
        * privileges they currently hold but were not requested
        * privileges requested that they do not hold
    """
    cur_privs = get_table_privileges(cursor, user, table)
    have_currently = cur_privs.intersection(privs)
    other_current = cur_privs.difference(privs)
    desired = privs.difference(cur_privs)
    return (have_currently, other_current, desired)


def get_table_privileges(cursor, user, table):
    if '.' in table:
        schema, table = table.split('.', 1)
    else:
        schema = 'public'
    query = '''SELECT privilege_type FROM information_schema.role_table_grants
    WHERE grantee=%s AND table_name=%s AND table_schema=%s'''
    cursor.execute(query, (user, table, schema))
    return frozenset([x[0] for x in cursor.fetchall()])


def grant_table_privileges(cursor, user, table, privs):
    # Note: priv escaped by parse_privs
    privs = ', '.join(privs)
    query = 'GRANT %s ON TABLE %s TO %s' % (
        privs, pg_quote_identifier(table, 'table'), pg_quote_identifier(user, 'role'))
    cursor.execute(query)


def revoke_table_privileges(cursor, user, table, privs):
    # Note: priv escaped by parse_privs
    privs = ', '.join(privs)
    query = 'REVOKE %s ON TABLE %s FROM %s' % (
        privs, pg_quote_identifier(table, 'table'), pg_quote_identifier(user, 'role'))
    cursor.execute(query)


def get_database_privileges(cursor, user, db):
    priv_map = {
        'C': 'CREATE',
        'T': 'TEMPORARY',
        'c': 'CONNECT',
    }
    query = 'SELECT datacl FROM pg_database WHERE datname = %s'
    cursor.execute(query, (db,))
    datacl = cursor.fetchone()[0]
    if datacl is None:
        return set()
    r = re.search('%s\\\\?\"?=(C?T?c?)/[^,]+\,?' % user, datacl)
    if r is None:
        return set()
    o = set()
    for v in r.group(1):
        o.add(priv_map[v])
    return normalize_privileges(o, 'database')


def has_database_privileges(cursor, user, db, privs):
    """
    Return the difference between the privileges that a user already has and
    the privileges that they desire to have.

    :returns: tuple of:
        * privileges that they have and were requested
        * privileges they currently hold but were not requested
        * privileges requested that they do not hold
    """
    cur_privs = get_database_privileges(cursor, user, db)
    have_currently = cur_privs.intersection(privs)
    other_current = cur_privs.difference(privs)
    desired = privs.difference(cur_privs)
    return (have_currently, other_current, desired)


def grant_database_privileges(cursor, user, db, privs):
    # Note: priv escaped by parse_privs
    privs = ', '.join(privs)
    if user == "PUBLIC":
        query = 'GRANT %s ON DATABASE %s TO PUBLIC' % (
                privs, pg_quote_identifier(db, 'database'))
    else:
        query = 'GRANT %s ON DATABASE %s TO %s' % (
                privs, pg_quote_identifier(db, 'database'),
                pg_quote_identifier(user, 'role'))
    cursor.execute(query)


def revoke_database_privileges(cursor, user, db, privs):
    # Note: priv escaped by parse_privs
    privs = ', '.join(privs)
    if user == "PUBLIC":
        query = 'REVOKE %s ON DATABASE %s FROM PUBLIC' % (
                privs, pg_quote_identifier(db, 'database'))
    else:
        query = 'REVOKE %s ON DATABASE %s FROM %s' % (
                privs, pg_quote_identifier(db, 'database'),
                pg_quote_identifier(user, 'role'))
    cursor.execute(query)


def revoke_privileges(cursor, user, privs):
    if privs is None:
        return False

    revoke_funcs = dict(table=revoke_table_privileges,
                        database=revoke_database_privileges)
    check_funcs = dict(table=has_table_privileges,
                       database=has_database_privileges)

    changed = False
    for type_ in privs:
        for name, privileges in iteritems(privs[type_]):
            # Check that any of the privileges requested to be removed are
            # currently granted to the user
            differences = check_funcs[type_](cursor, user, name, privileges)
            if differences[0]:
                revoke_funcs[type_](cursor, user, name, privileges)
                changed = True
    return changed


def grant_privileges(cursor, user, privs):
    if privs is None:
        return False

    grant_funcs = dict(table=grant_table_privileges,
                       database=grant_database_privileges)
    check_funcs = dict(table=has_table_privileges,
                       database=has_database_privileges)

    changed = False
    for type_ in privs:
        for name, privileges in iteritems(privs[type_]):
            # Check that any of the privileges requested for the user are
            # currently missing
            differences = check_funcs[type_](cursor, user, name, privileges)
            if differences[2]:
                grant_funcs[type_](cursor, user, name, privileges)
                changed = True
    return changed


def parse_role_attrs(cursor, role_attr_flags):
    """
    Parse role attributes string for user creation.
    Format:

        attributes[,attributes,...]

    Where:

        attributes := CREATEDB,CREATEROLE,NOSUPERUSER,...
        [ "[NO]SUPERUSER","[NO]CREATEROLE", "[NO]CREATEUSER", "[NO]CREATEDB",
                            "[NO]INHERIT", "[NO]LOGIN", "[NO]REPLICATION",
                            "[NO]BYPASSRLS" ]

    Note: "[NO]BYPASSRLS" role attribute introduced in 9.5

    """
    flags = frozenset(role.upper() for role in role_attr_flags.split(',') if role)

    valid_flags = frozenset(itertools.chain(FLAGS, get_valid_flags_by_version(cursor)))
    valid_flags = frozenset(itertools.chain(valid_flags, ('NO%s' % flag for flag in valid_flags)))

    if not flags.issubset(valid_flags):
        raise InvalidFlagsError('Invalid role_attr_flags specified: %s' %
                                ' '.join(flags.difference(valid_flags)))

    return ' '.join(flags)


def normalize_privileges(privs, type_):
    new_privs = set(privs)
    if 'ALL' in new_privs:
        new_privs.update(VALID_PRIVS[type_])
        new_privs.remove('ALL')
    if 'TEMP' in new_privs:
        new_privs.add('TEMPORARY')
        new_privs.remove('TEMP')

    return new_privs


def parse_privs(privs, db):
    """
    Parse privilege string to determine permissions for database db.
    Format:

        privileges[/privileges/...]

    Where:

        privileges := DATABASE_PRIVILEGES[,DATABASE_PRIVILEGES,...] |
            TABLE_NAME:TABLE_PRIVILEGES[,TABLE_PRIVILEGES,...]
    """
    if privs is None:
        return privs

    o_privs = {
        'database': {},
        'table': {}
    }
    for token in privs.split('/'):
        if ':' not in token:
            type_ = 'database'
            name = db
            priv_set = frozenset(x.strip().upper()
                                 for x in token.split(',') if x.strip())
        else:
            type_ = 'table'
            name, privileges = token.split(':', 1)
            priv_set = frozenset(x.strip().upper()
                                 for x in privileges.split(',') if x.strip())

        if not priv_set.issubset(VALID_PRIVS[type_]):
            raise InvalidPrivsError('Invalid privs specified for %s: %s' %
                                    (type_, ' '.join(priv_set.difference(VALID_PRIVS[type_]))))

        priv_set = normalize_privileges(priv_set, type_)
        o_privs[type_][name] = priv_set

    return o_privs


def get_pg_server_version(cursor):
    """
    Queries Postgres for its server version.

    server_version should be just the server version itself:

    postgres=# SHOW SERVER_VERSION;
    server_version
    ----------------
     9.6.2
    (1 row)
    """
    cursor.execute("SHOW SERVER_VERSION")
    return cursor.fetchone()['server_version']


def get_valid_flags_by_version(cursor):
    """
    Some role attributes were introduced after certain versions. We want to
    compile a list of valid flags against the current Postgres version.
    """
    current_version = StrictVersion(get_pg_server_version(cursor))

    return [
        flag
        for flag, version_introduced in FLAGS_BY_VERSION.items()
        if current_version >= StrictVersion(version_introduced)
    ]


# ===========================================
# Module execution.
#


def main():
    module = AnsibleModule(
        argument_spec=dict(
            login_user=dict(default="postgres"),
            login_password=dict(default="", no_log=True),
            login_host=dict(default=""),
            login_unix_socket=dict(default=""),
            user=dict(required=True, aliases=['name']),
            password=dict(default=None, no_log=True),
            state=dict(default="present", choices=["absent", "present"]),
            priv=dict(default=None),
            db=dict(default=''),
            port=dict(default='5432'),
            fail_on_user=dict(type='bool', default='yes'),
            role_attr_flags=dict(default=''),
            encrypted=dict(type='bool', default='no'),
            no_password_changes=dict(type='bool', default='no'),
            expires=dict(default=None),
            ssl_mode=dict(default='prefer', choices=[
                          'disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full']),
            ssl_rootcert=dict(default=None)
        ),
        supports_check_mode=True
    )

    user = module.params["user"]
    password = module.params["password"]
    state = module.params["state"]
    fail_on_user = module.params["fail_on_user"]
    db = module.params["db"]
    if db == '' and module.params["priv"] is not None:
        module.fail_json(msg="privileges require a database to be specified")
    privs = parse_privs(module.params["priv"], db)
    no_password_changes = module.params["no_password_changes"]
    if module.params["encrypted"]:
        encrypted = "ENCRYPTED"
    else:
        encrypted = "UNENCRYPTED"
    expires = module.params["expires"]
    sslrootcert = module.params["ssl_rootcert"]

    if not postgresqldb_found:
        module.fail_json(msg="the python psycopg2 module is required")

    # To use defaults values, keyword arguments must be absent, so
    # check which values are empty and don't include in the **kw
    # dictionary
    params_map = {
        "login_host": "host",
        "login_user": "user",
        "login_password": "password",
        "port": "port",
        "db": "database",
        "ssl_mode": "sslmode",
        "ssl_rootcert": "sslrootcert"
    }
    kw = dict((params_map[k], v) for (k, v) in iteritems(module.params)
              if k in params_map and v != "" and v is not None)

    # If a login_unix_socket is specified, incorporate it here.
    is_localhost = "host" not in kw or kw["host"] == "" or kw["host"] == "localhost"
    if is_localhost and module.params["login_unix_socket"] != "":
        kw["host"] = module.params["login_unix_socket"]

    if psycopg2.__version__ < '2.4.3' and sslrootcert is not None:
        module.fail_json(
            msg='psycopg2 must be at least 2.4.3 in order to user the ssl_rootcert parameter')

    try:
        db_connection = psycopg2.connect(**kw)
        cursor = db_connection.cursor(
            cursor_factory=psycopg2.extras.DictCursor)

    except TypeError as e:
        if 'sslrootcert' in e.args[0]:
            module.fail_json(
                msg='Postgresql server must be at least version 8.4 to support sslrootcert')
        module.fail_json(msg="unable to connect to database: %s" % to_native(e), exception=traceback.format_exc())

    except Exception as e:
        module.fail_json(msg="unable to connect to database: %s" % to_native(e), exception=traceback.format_exc())

    try:
        role_attr_flags = parse_role_attrs(cursor, module.params["role_attr_flags"])
    except InvalidFlagsError as e:
        module.fail_json(msg=to_native(e), exception=traceback.format_exc())

    kw = dict(user=user)
    changed = False
    user_removed = False

    if state == "present":
        if user_exists(cursor, user):
            try:
                changed = user_alter(db_connection, module, user, password,
                                     role_attr_flags, encrypted, expires, no_password_changes)
            except SQLParseError as e:
                module.fail_json(msg=to_native(e), exception=traceback.format_exc())
        else:
            try:
                changed = user_add(cursor, user, password,
                                   role_attr_flags, encrypted, expires)
            except SQLParseError as e:
                module.fail_json(msg=to_native(e), exception=traceback.format_exc())
        try:
            changed = grant_privileges(cursor, user, privs) or changed
        except SQLParseError as e:
            module.fail_json(msg=to_native(e), exception=traceback.format_exc())
    else:
        if user_exists(cursor, user):
            if module.check_mode:
                changed = True
                kw['user_removed'] = True
            else:
                try:
                    changed = revoke_privileges(cursor, user, privs)
                    user_removed = user_delete(cursor, user)
                except SQLParseError as e:
                    module.fail_json(msg=to_native(e), exception=traceback.format_exc())
                changed = changed or user_removed
                if fail_on_user and not user_removed:
                    msg = "unable to remove user"
                    module.fail_json(msg=msg)
                kw['user_removed'] = user_removed

    if changed:
        if module.check_mode:
            db_connection.rollback()
        else:
            db_connection.commit()

    kw['changed'] = changed
    module.exit_json(**kw)


if __name__ == '__main__':
    main()
