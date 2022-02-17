#!/usr/bin/python3
# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import sys
import os
import yaml
from yaml import Dumper
import six
import configparser
from urllib.parse import urlparse
from collections import OrderedDict
from yaml.representer import SafeRepresenter

try:
    import click
except ImportError:
    print("click not installed\n pip install click")
    sys.exit(0)

# https://gist.github.com/oglops/c70fb69eef42d40bed06


def dict_representer(dumper, data):
    return dumper.represent_dict(six.iteritems(data))


def dict_constructor(loader, node):
    return OrderedDict(loader.construct_pairs(node))


Dumper.add_representer(OrderedDict, dict_representer)

Dumper.add_representer(str, SafeRepresenter.represent_str)


@click.group()
def buildout2doodba():
    pass


@buildout2doodba.command()
@click.argument("buildout_configuration_file", nargs=1, type=click.Path(exists=True))
@click.argument("doodba_dir", nargs=1, type=click.Path(exists=True))
def convert_addons(buildout_configuration_file, doodba_dir):
    """
    Convierte los datos de repositorios de buildout en el formato de doodba.

    BUILDOUT_CONFIGURATION_FILE: ruta del fichero de configuración base de buildout p.e.: base-only-odoo.cfg
    DOODBA_DIR: ruta del proyecto doodba
    """
    config = configparser.ConfigParser()
    config.read(buildout_configuration_file)
    repos_yaml = OrderedDict()
    addons_yaml = OrderedDict()
    merges_parsed_info = []
    if "odoo" in config and "merges" in config["odoo"]:
        # format git origin odoo-repos/project pull/293/head
        merges_dict = config["odoo"]["merges"]
        if isinstance(merges_dict, str):
            merges_dict = [merges_dict]
        for merge in merges_dict:
            if not merge.startswith("git"):
                continue
            merge_data = merge.split(" ")
            merges_parsed_info.append(
                {
                    "remote": merge_data[1],
                    "build_path": merge_data[2],
                    "pull_data": merge_data[3],
                }
            )
    build_merge_paths = [x["build_path"] for x in merges_parsed_info]
    if "odoo" in config and "addons" in config["odoo"]:
        # format git https://github.com/OCA/XXXX.git odoo-repos/XXXX 10.0
        for repo in config["odoo"]["addons"].split("\n"):
            if not repo.startswith("git"):
                print("repository {} not added".format(repo))
                continue
            if "git@" in repo:
                print("Repositorio {} añadido mediante SSH".format(repo))
            repo_data = repo.split(" ")
            url_path = urlparse(repo_data[1])
            repo_name = url_path.path.split("/")[-1].replace(".git", "")
            if "/OCA/" not in repo_data[1].upper() or repo_data[2] in build_merge_paths:
                repo_dict = OrderedDict()
                repo_dict["defaults"] = {"depth": "$DEPTH_MERGE"}
                repo_dict["remotes"] = {"origin": repo_data[1]}
                repo_dict["target"] = "origin $ODOO_VERSION"
                repo_dict["merges"] = ["origin $ODOO_VERSION"]

                repos_yaml[repo_name] = repo_dict
                for merge in filter(
                    lambda d: d["build_path"] == repo_data[2], merges_parsed_info
                ):
                    remote_name = "origin"
                    if merge["remote"] != "origin":
                        remote_name = "cmnt"
                        repos_yaml[repo_name]["rempotes"]["cmnt"] = merge["remote"]
                    repos_yaml[repo_name]["merges"].append(
                        "{} {}".format(remote_name, merge["pull_data"])
                    )
            addons_yaml[repo_name] = ["*"]
    repos_yaml_path = os.path.join(doodba_dir, "odoo/custom/src/repos.yaml")
    with open(repos_yaml_path, "a") as repos_file:
        repos_file.write(yaml.dump(repos_yaml, Dumper=Dumper, default_flow_style=False))

    addons_yaml_path = os.path.join(doodba_dir, "odoo/custom/src/addons.yaml")
    with open(addons_yaml_path, "a") as addons_file:
        addons_yaml_content = yaml.dump(
            addons_yaml, Dumper=Dumper, default_flow_style=False
        )
        addons_file.write(addons_yaml_content.replace("'", '"'))


if __name__ == "__main__":
    buildout2doodba()
