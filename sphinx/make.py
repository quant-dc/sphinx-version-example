from pathlib import Path
import sys
import subprocess
import shutil
import packaging
import json

import click
from loguru import logger

DOC_PATH = Path(__file__).parent
SOURCE_PATH = DOC_PATH / "source"
SWITCHER_PATH = SOURCE_PATH / "_static" / "switcher.json"
BUILD_PATH = DOC_PATH / "build"
sys.path.append(str(DOC_PATH.parent))

import src

@click.group()
def main():
    ...

@main.command()
@click.option("--kind", default="html")
@click.option("--num_jobs", default="auto")
def build(kind, num_jobs):
    destination = BUILD_PATH / kind
    version_file = destination / ".version"
    src_version = packaging.version.parse(src.__version__)
    if SWITCHER_PATH.exists():
        with open(SWITCHER_PATH, mode="r") as f:
            switcher = json.loads(f.read())
    else:
        switcher = []
    if destination.exists():
        history_destination = destination / "archive"
        history_destination.mkdir(exist_ok=True)
        if version_file.exists():
            with open(version_file, mode="r") as f:
                version = packaging.version.parse(f.read())
            if version < src_version:
                logger.debug("Archiving previous documentation")
                switcher = [
                    data for data in switcher if data["name"] != "Latest"
                ]
                switcher += [
                    {
                        "name": "Latest",
                        "version": str(src_version),
                        "url": "https://quant-dc.github.io/sphinx-version-example/index.html",
                    },
                    {
                        "name": str(version),
                        "version": str(version),
                        "url": f"https://quant-dc.github.io/sphinx-version-example/archive/{version}/index.html",
                    },
                ]
                old_version_destination = history_destination / str(version)
                old_version_destination.mkdir(exist_ok=True)
                files = set(destination.glob("*/")) # Shift old documentation
                files.remove(history_destination)
                for file in files:
                    file.rename(old_version_destination / file.name)
            elif version > src_version:
                logger.debug("Version is older than current documentation")
                logger.debug("Writing to archive folder")
                destination = history_destination / str(src_version)
                switcher = [
                    data for data in switcher
                    if data["version"] != str(src_version)
                ]
                switcher += [
                    {
                        "name": str(src_version),
                        "version": str(src_version),
                        "url": "...",
                    }
                ]
            else:
                logger.debug("Overwriting documentation of the same version")
    else:
        logger.debug("Starting a fresh set of documentation")
        switcher = [{
            "name": "Latest",
            "version": str(src_version),
            "url": "...",
        }]
    with open(SWITCHER_PATH, mode="w") as f:
        f.write(json.dumps(switcher))

    cmd = [
        "sphinx-build",
        "-b", kind,
        "-j", num_jobs,
        "-d", str(BUILD_PATH / "doctrees"),
        str(SOURCE_PATH),
        str(destination)
    ]
    subprocess.call(cmd)
    if not version_file.exists():
        with open(version_file, mode="w") as f:
            f.write(src.__version__)

    if kind == "html":
        gh_pages_folder = DOC_PATH.parent / "docs"
        shutil.rmtree(gh_pages_folder)
        shutil.copytree(
            BUILD_PATH / "html", gh_pages_folder, dirs_exist_ok=True
        )

@main.command()
@click.option("--current/--all", default=False)
def clean(current):
    destination = BUILD_PATH / "html"
    history_destination = destination / "previous"
    paths = destination.glob("*/")
    for path in paths:
        if path == history_destination and current:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    if not current:
        destination.rmdir()
        SWITCHER_PATH.unlink()


if __name__ == "__main__":
    main()