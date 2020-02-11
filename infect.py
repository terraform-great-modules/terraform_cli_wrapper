#!/usr/bin/env python3
"""Infect terraform git repositories with shell wrappers.

Expected folder structure:
 - /: project root
 - /<environment>: single project environment
 - /modules: list of common modules
 - /scripts/Makefile: make file for project management
"""
import subprocess
import os
import shutil
import re
import hashlib
import json
import difflib
import sys
import click


CARRIER = os.path.dirname(os.path.realpath(__file__))

def read_config():
    """Read current configuration file"""
    with open("config.json", "r") as cfile:
        return json.load(cfile)
CONF = read_config()

def path_project_makefile_dir(project_path):
    """Where Makefile is stored"""
    return os.path.join(project_path, "scripts")

def path_project_makefile(project_path):
    """Where Makefile is stored"""
    return os.path.join(path_project_makefile_dir(project_path), "Makefile")

def path_modules(project_path):
    """Where Makefile is stored"""
    return os.path.join(project_path, "modules")

def path_mod_make(project_path):
    """Modules' makefile"""
    return os.path.join(path_modules(project_path), "Makefile")

def path_mod_scripts(project_path):
    """Modules' makefile"""
    return os.path.join(path_modules(project_path), "scripts")

def make_version(makefile):
    """Return current project makefile version"""
    if os.path.isfile(makefile):
        makefile = os.path.dirname(makefile)
    try:
        make = subprocess.run(["make", "version"], check=True,
                              cwd=makefile,
                              stdout=subprocess.PIPE)
    except subprocess.CalledProcessError:
        click.echo(f"Some error to run make for project file {makefile}")
        return None
    return make.stdout.decode('utf-8').strip()

def project_makefile_vers(project_path):
    """Return current project makefile version"""
    makefilefolder = path_project_makefile_dir(project_path)
    return make_version(makefilefolder)

def project_makefile_check(project_path):
    """Check project makefile version against current.
    Return:
        (True/False, wanted_version, found_version)"""
    if not os.path.isdir(project_path):
        click.echo(f"The path {project_path} doesn't exist. Quitting.")
        raise FileNotFoundError(f"The path {project_path} doesn't exist. Quitting.")
    source = project_makefile_vers(CARRIER)
    dest = project_makefile_vers(project_path)
    return source == dest, source, dest

def project_makefile_infect(project_path):
    """Infect the project with wanted makefile"""
    scripts = os.path.join(project_path, "scripts")
    source = path_project_makefile(CARRIER)
    dest = path_project_makefile(project_path)
    if not os.path.isdir(project_path):
        click.echo(f"The path {project_path} doesn't exist. Quitting.")
        raise FileNotFoundError(f"The path {project_path} doesn't exist. Quitting.")
    if not os.path.isdir(scripts):
        os.mkdir(scripts)
    vers = project_makefile_check(project_path)
    if vers[0]:
        click.echo("Versions matched")
        return
    if os.path.isfile(dest):
        click.echo(f"Found Makefile differences: wanted => {vers[1]}, found => {vers[2]}")
        click.echo("")
        with open(source) as _sf, open(dest) as _df:
            fromlines = _df.readlines()
            tolines = _sf.readlines()
        diff = difflib.unified_diff(fromlines, tolines,
                                    fromfile="to_be_override", tofile="updated", n=3)
        sys.stdout.writelines(diff)
    if click.confirm(f"Confirm to override file {dest}"):
        shutil.copy(source, dest)
        click.echo(f"File {source} written over {dest}")
    else:
        click.echo("Skipping...")

def project_makefile_symlink(project_path):
    """Create default symlink to main Makefile"""
    for folder in [i for i in os.listdir(project_path) \
            if os.path.isdir(os.path.join(project_path, i))]:
        if folder in ["scripts", "patch", "patches", "modules", "tmp"]:
            continue
        if folder.startswith("."):
            continue
        dest = os.path.join(project_path, folder, "Makefile")
        if not "Makefile" in os.listdir(os.path.dirname(dest)):
            if click.confirm(f"Confirm to create Makefile symlink in {dest}?"):
                os.symlink("../scripts/Makefile", dest)
            continue
        if not os.path.islink(dest):
            click.echo("Found Makefile in {folder}, but it is not a symlink")

def sh_version(filepath):
    """Read tag "# Version" from any script"""
    version = None
    pattern = re.compile('# *version *:* *([^ ]+)', re.IGNORECASE)
    maxline = 100
    with open(filepath, 'r') as _f:
        line = 0
        while line < maxline:
            matches = pattern.match(_f.readline())
            if matches:
                version = matches.group(1)
                break
            line += 1
    return version

BLOCKSIZE = 65536
def file_hash(filepath):
    """Return file hash"""
    hasher = hashlib.sha1()
    with open(filepath, 'r') as _f:
        buf = _f.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = _f.read(BLOCKSIZE)
    return hasher.hexdigest()

def infect_module_make(source, dest):
    """Align makefiles"""
    if os.path.isfile(dest):
        if make_version(source) == make_version(dest):
            click.echo("Modules makefile are already aligned")
            return
        click.echo((f"Found Makefile differences: ",
                    f"wanted => {make_version(source)}, found => {make_version(dest)}"))
        click.echo("")
        with open(source) as _sf, open(dest) as _df:
            fromlines = _df.readlines()
            tolines = _sf.readlines()
        diff = difflib.unified_diff(fromlines, tolines,
                                    fromfile="to_be_override", tofile="updated", n=3)
        sys.stdout.writelines(diff)
    if click.confirm(f"Confirm to override file {dest}"):
        shutil.copy(source, dest)
        click.echo(f"File {source} written over {dest}")
    else:
        click.echo("Skipping...")

def infect_module_scripts(project_path):
    """Infect modules/scripts"""
    scripts_source = path_mod_scripts(CARRIER)
    scripts_dest = path_mod_scripts(project_path)
    for root, dirs, files in os.walk(scripts_source, followlinks=False):
        droot = os.path.join(scripts_dest, root[len(scripts_source):])
        for name in dirs:
            if not os.path.isdir(droot) and \
                    click.confirm(f"Confirm to create dir {droot}/{name}"):
                os.mkdir(os.path.join(droot, name))
        for name in files:
            fsource = os.path.join(root, name)
            fdest = os.path.join(droot, name)
            if os.path.isfile(fdest):
                if sh_version(fsource) == sh_version(fdest):
                    click.echo(f"File {fdest} already aligned")
                    continue
                click.echo((f"Found file differences: ",
                            f"wanted => {sh_version(fsource)}, found => {sh_version(fdest)}"))
                click.echo("")
                with open(fsource) as _sf, open(fdest) as _df:
                    fromlines = _df.readlines()
                    tolines = _sf.readlines()
                diff = difflib.unified_diff(fromlines, tolines,
                                            fromfile="to_be_override", tofile="updated", n=3)
                sys.stdout.writelines(diff)
            if click.confirm(f"Confirm to override file {fdest}"):
                shutil.copy(fsource, fdest)
                click.echo(f"File {fsource} written over {fdest}")
            else:
                click.echo("Skipping...")

def project_modules_infect(project_path):
    """Infect the project with the modules folder."""
    modules = path_modules(project_path)
    if not os.path.isdir(modules):
        if click.confirm(f"Module folder {modules} not found, can it be created?"):
            shutil.copy(path_modules(CARRIER), modules)
            click.echo(f"Directory initialized into {modules}")
        else:
            click.echo("Nothing to do, skipping...")
        return
    makef = (path_mod_make(CARRIER), path_mod_make(project_path))
    infect_module_make(*makef)
    infect_module_scripts(project_path)


@click.group()
def cli():  # pylint: disable=missing-function-docstring
    pass

@cli.command()
def infect_all():
    """Infect all available project from ./config.json"""
    for prj_path in CONF.get("paths"):
        click.echo(f"Working on project {os.path.abspath(prj_path)}")
        project_makefile_infect(prj_path)
        project_makefile_symlink(prj_path)
        project_modules_infect(prj_path)

if __name__ == '__main__':
    cli()
