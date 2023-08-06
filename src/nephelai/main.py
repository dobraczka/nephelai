from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from .api import download as nephelai_download
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
    nephelai_upload(
        file_to_upload=file_to_upload,
        nc_path=nc_path,
        chunk_size=chunk_size,
        debug=debug,
    )


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
    nephelai_download(remote_path=remote_path, local_path=local_path)


if __name__ == "__main__":
    app()
