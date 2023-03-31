"""PEP 517 build backend wrapper for optionally pre-building docs for sdist."""

from __future__ import annotations

import os
import re
import sys
import typing as t
from configparser import ConfigParser
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory

try:
    from contextlib import chdir as _chdir_cm
except ImportError:
    @contextmanager
    def _chdir_cm(path: os.PathLike) -> t.Iterator[None]:
        original_wd = Path.cwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(original_wd)

from setuptools.build_meta import (
    build_sdist as _setuptools_build_sdist,
    get_requires_for_build_sdist as _setuptools_get_requires_for_build_sdist,
)


__all__ = (  # noqa: WPS317, WPS410
    'build_sdist', 'get_requires_for_build_sdist',
)


BUILD_MANPAGES_CONFIG_SETTING = '--build-manpages'
"""Config setting name toggle that is used to request manpage in sdists."""


@contextmanager
def _run_in_temporary_directory() -> t.Iterator[Path]:
    with TemporaryDirectory(prefix='.tmp-ansible-pep517-') as tmp_dir:
        with _chdir_cm(tmp_dir):
            yield Path(tmp_dir)


def _make_in_tree_ansible_importable() -> None:
    """Add the library directory to module lookup paths."""
    lib_path = str(Path.cwd() / 'lib/')
    sys.path.insert(0, lib_path)  # NOTE: for the current runtime session


def _get_package_distribution_version() -> str:
    """Retrieve the current version number from setuptools config."""
    setup_cfg_path = Path.cwd() / 'setup.cfg'
    setup_cfg = ConfigParser()
    setup_cfg.read_string(setup_cfg_path.read_text())
    cfg_version = setup_cfg.get('metadata', 'version')
    importable_version_str = cfg_version.removeprefix('attr: ')
    version_mod_str, version_var_str = importable_version_str.rsplit('.', 1)
    _make_in_tree_ansible_importable()
    return getattr(import_module(version_mod_str), version_var_str)


def build_sdist(  # noqa: WPS210, WPS430
         sdist_directory: os.PathLike,
         config_settings: dict[str, str] | None = None,
) -> str:
    build_manpages_requested = BUILD_MANPAGES_CONFIG_SETTING in (
        config_settings or {}
    )
    original_src_dir = Path.cwd().resolve()
    with _run_in_temporary_directory() as tmp_dir:
        tmp_src_dir = Path(tmp_dir) / 'src'
        copytree(original_src_dir, tmp_src_dir)
        os.chdir(tmp_src_dir)

        if build_manpages_requested:
            version_number = _get_package_distribution_version()
            from .man import build_man_pages, DEFAULT_RELATIVE_OUTPUT_DIR
            build_man_pages(version_number, tmp_src_dir / DEFAULT_RELATIVE_OUTPUT_DIR)

        Path('pyproject.toml').write_text(
            re.sub(
                r"""(?x)
                backend-path\s=\s\[  # value is a list of double-quoted strings
                    [^]]+
                ].*\n
                build-backend\s=\s"[^"]+".*\n  # value is double-quoted
                """,
                'build-backend = "setuptools.build_meta"\n',
                Path('pyproject.toml').read_text(),
            )
        )

        built_sdist_basename = _setuptools_build_sdist(
            sdist_directory=sdist_directory,
            config_settings=config_settings,
        )

    return built_sdist_basename


def get_requires_for_build_sdist(
        config_settings: dict[str, str] | None = None,
) -> list[str]:
    build_manpages_requested = BUILD_MANPAGES_CONFIG_SETTING in (
        config_settings or {}
    )
    build_manpages_requested = True  # FIXME: Once pypa/build#559 is addressed.

    manpage_build_deps = [
        'docutils',  # provides `rst2man`
        'jinja2',  # used in `hacking/build-ansible.py generate-man`
        'pyyaml',  # needed for importing in-tree `ansible-core` from `lib/`
    ] if build_manpages_requested else []

    return _setuptools_get_requires_for_build_sdist(
        config_settings=config_settings,
    ) + manpage_build_deps
