from pathlib import Path
from typing import Optional

import owncloud
import typer
from typing_extensions import Annotated

from .api import download as nephelai_download
from .api import get_oc
from .api import upload as nephelai_upload

app = typer.Typer()


@app.command()
def upload(
    file_to_upload: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=True,
            writable=False,
            readable=True,
            resolve_path=False,
        ),
    ],
    nc_path: str,
    chunk_size: str = "100MiB",
    debug: bool = False,
):
    res = nephelai_upload(
        file_to_upload=file_to_upload,
        nc_path=nc_path,
        chunk_size=chunk_size,
        debug=debug,
    )
    if res is not None:
        typer.echo("Successfully uploaded '{file_to_upload}'!")


@app.command()
def upload_with_fs(
    file_to_upload: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=True,
            writable=False,
            readable=True,
            resolve_path=False,
        ),
    ],
    chunk_size: str = "100MiB",
    debug: bool = False,
):
    upload(file_to_upload, str(file_to_upload), chunk_size=chunk_size, debug=debug)


@app.command()
def download(remote_path: str, local_path: Optional[str] = None):
    res = nephelai_download(remote_path=remote_path, local_path=local_path)
    if res is None:
        typer.echo(f"Path '{remote_path}' does not exist...")
    else:
        typer.echo(f"Successfully downloaded '{remote_path}'!")


@app.command()
def ls(remote_path: str):
    oc = get_oc()
    try:
        file_list = oc.list(remote_path)
        typer.echo(f"Listing files in '{remote_path}':")
        for file in file_list:
            typer.echo(file.path)
    except owncloud.owncloud.HTTPResponseError as err:
        if err.status_code == 404:
            typer.echo(f"Path '{remote_path}' does not exist...")
        else:
            raise err


if __name__ == "__main__":
    app()
