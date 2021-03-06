#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

import datetime
import os
from invoke import task
import fotc.database

DEFAULT_REPOSITORY = "hstefanp/fotc"
DOCKERFILE = "./docker/Dockerfile"


@task
def docker_build(ctx, repository=DEFAULT_REPOSITORY):
    """
    Builds and tags fotc's docker image

    :type ctx: invoke.Context
    :type repository: str
    """
    commit = ctx.run("git describe --always --long --tags --broken")
    if commit.failed:
        print("Failed to get git version!")
        return
    commit = commit.stdout.strip()
    date = datetime.datetime.utcnow().strftime("%Y%m%d%H%M")
    tag = f"{repository}:{date}-{commit}"
    latest = f"{repository}:latest"
    ctx.run(f"docker build . -f {DOCKERFILE} -t {tag} -t {latest}")


def _docker_login_command():
    username = os.environ["DOCKER_USERNAME"]
    password = os.environ["DOCKER_PASSWORD"]
    return f"docker login --username={username} --password={password}"


@task
def docker_push(ctx, repository=DEFAULT_REPOSITORY, tag_filter=None):
    """
    Pushes locally built images to the Docker repository

    :type ctx: invoke.Context
    :type repository: str
    :type tag_filter: str|None
    """
    target = f"{repository}:{tag_filter}" if tag_filter else f"{repository}"
    images_format = "{{.Repository}}:{{.Tag}}"
    images_out = ctx.run(f"docker images {target} --format {images_format}").stdout
    images = [x for x in images_out.split('\n') if x]
    print(images)

    with ctx.prefix(_docker_login_command()):
        for image in images:
            ctx.run(f"docker push {image}")


@task
def test(ctx, dir_path="./tests/"):
    """
    Run test suite on dir_path

    :type ctx: invoke.Context
    :type dir_path: str
    """
    ctx.run(f"python -m pytest {dir_path}")


@task()
def create_db_tables(_ctx, drop=False):
    """
    Create database tables from the defined modules

    :type _ctx: invoke.Context
    """
    conn = fotc.database.get_default_engine().connect()
    if drop:
        with open('database/drop-all.sql') as drop:
            conn.execute(drop.read())

    with open('database/schema.sql') as schema:
        conn.execute(schema.read())