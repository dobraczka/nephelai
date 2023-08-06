import logging
import math
import os
import pathlib
from typing import Final, Literal, Optional, Tuple, Union

import bitmath
import owncloud
from dotenv import load_dotenv
from tqdm.auto import tqdm, trange

_DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024

logger = logging.getLogger("nephelai")
CHUNKED_SUFFIX = "_chunked"

NEXTCLOUD_FOLDER_URI_KEY = "NEXTCLOUD_FOLDER_URI"
NEXTCLOUD_FOLDER_PW_KEY = "NEXTCLOUD_FOLDER_PW"

FileStateExists: Final = "FILE_EXISTS_AND_IS_NOT_DIR"
FileStateExistsChunked: Final = "FILE_IS_CHUNKED"
FileStateIsDirUnchunked: Final = "FILE_IS_UNCHUNKED_DIR"
FileStateDoesNotExist: Final = "FILE_DOES_NOT_EXIST"
FileState = Literal[
    "FILE_EXISTS_AND_IS_NOT_DIR",
    "FILE_IS_CHUNKED",
    "FILE_IS_UNCHUNKED_DIR",
    "FILE_DOES_NOT_EXIST",
]


def _remove_commonpath(full_path: str, base: str):
    return os.path.relpath(full_path, os.path.commonpath([base, full_path]))


def create_nc_folders(my_dir: pathlib.Path, nc_client: owncloud.Client) -> bool:
    """Create nextcloud folders using given owncloud client.

    Will create all subpaths if needed.

    Args:
        my_dir: Full path to create
        nc_client: Client with shared folder

    Returns:
        True if folders did not exist, False otherwise
    """
    accumulated_part = ""
    had_to_create = False
    for dir_part in my_dir.parts:
        accumulated_part = os.path.join(accumulated_part, dir_part)
        try:
            nc_client.file_info(accumulated_part)
        except owncloud.owncloud.HTTPResponseError as oc_error:
            if oc_error.status_code == 404:
                nc_client.mkdir(accumulated_part)
                had_to_create = True
    return had_to_create


def chunked_upload(
    nc_client: owncloud.Client,
    local_source_file: pathlib.Path,
    remote_path: str,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    keep_mtime: bool = True,
) -> bool:
    """Upload file to remote by creating a folder containing chunks if needed.

    Chunks are enumerated from 000000000000001 until the final chunk.
    The folder will be named `remote_path` + `_chunked`.
    If the file is smaller than the `chunk_size`, will try to upload
    file in one piece.

    Args:
        nc_client: Client with shared folder
        local_source_file: Local file to upload
        remote_path: Path where file be stored remotely.
        chunk_size: Chunk size in bytes.
        keep_mtime: If True sends modified time in header.

    Returns:
        True if successful

    Raises:
        ServerError: owncloud.owncloud.HTTPResponseError if server throws error
    """
    result = True

    remote_path = nc_client._normalize_path(remote_path)
    if remote_path.endswith("/"):
        remote_path += os.path.basename(local_source_file)

    original_remote_path = remote_path
    create_nc_folders(
        my_dir=pathlib.Path(original_remote_path).parent, nc_client=nc_client
    )
    remote_path += CHUNKED_SUFFIX + "/"

    stat_result = os.stat(local_source_file)

    file_handle = open(local_source_file, "rb", 8192)
    file_handle.seek(0, os.SEEK_END)
    size = file_handle.tell()

    if size <= chunk_size:
        return nc_client.put_file(
            remote_path=original_remote_path,
            local_source_file=local_source_file,
            chunked=False,
        )

    file_handle.seek(0)

    nc_client.mkdir(remote_path)
    headers = {}
    if keep_mtime:
        headers["X-OC-MTIME"] = str(int(stat_result.st_mtime))

    if size == 0:
        return nc_client._make_dav_request(
            "PUT", original_remote_path, data="", headers=headers
        )

    try:
        chunk_count = int(math.ceil(float(size) / float(chunk_size)))
        for chunk_index in trange(0, int(chunk_count), desc="Uploading chunks"):
            data = file_handle.read(chunk_size)
            chunk_name = f"{remote_path}{chunk_index:015d}"
            if not nc_client._make_dav_request(
                "PUT", chunk_name, data=data, headers=headers
            ):
                result = False
                break
    except owncloud.owncloud.HTTPResponseError as ServerError:
        nc_client.delete(remote_path)
        file_handle.close()
        raise ServerError
    file_handle.close()
    return result


def upload(
    file_to_upload: Union[pathlib.Path, str],
    nc_path: str,
    chunk_size: Union[int, str] = "100MiB",
    debug: bool = False,
) -> Optional[bool]:
    """Upload to password protected shared folder.

    If file is larger than `chunk_size` a folder will be created,
    and the chunks will be uploaded there.

    Args:
        file_to_upload: The file to upload
        nc_path: The remote path
        chunk_size: Chunk size as bytes or as human readable string
        debug: If True, show debug info

    Returns:
        True if successful, else None
    """
    if not isinstance(file_to_upload, pathlib.Path):
        file_to_upload = pathlib.Path(file_to_upload)
    if not isinstance(chunk_size, int):
        try:
            chunk_size = int(chunk_size)
        except ValueError:
            chunk_size = int(bitmath.parse_string(chunk_size).bytes)
    load_dotenv()
    oc = owncloud.Client.from_public_link(
        os.environ[NEXTCLOUD_FOLDER_URI_KEY],
        folder_password=os.environ[NEXTCLOUD_FOLDER_PW_KEY],
        debug=debug,
    )
    if file_to_upload.is_dir():
        create_nc_folders(file_to_upload, oc)
        for subfile in file_to_upload.iterdir():
            upload(
                subfile,
                os.path.join(nc_path, subfile.name),
                chunk_size=chunk_size,
                debug=debug,
            )
    else:
        chunked_upload(oc, file_to_upload, nc_path, chunk_size=chunk_size)
    return True


def _chunked_download(oc: owncloud.Client, remote_path: str, local_path: str):
    try:
        if os.path.exists(local_path):
            os.remove(local_path)
        parent_dir = pathlib.Path(local_path).parent
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        with open(local_path, "ba") as file_handle:
            for remote_file in tqdm(
                oc.list(remote_path),
                desc=f"Downloading chunks from {remote_path}",
            ):
                file_handle.write(oc.get_file_contents(remote_file.path))
    except owncloud.owncloud.HTTPResponseError as err:
        logger.info("File not found...")
        raise err


def _check_file_state_from_file_info(
    file_info: owncloud.FileInfo,
) -> Tuple[FileState, owncloud.FileInfo]:
    if file_info.path.endswith(CHUNKED_SUFFIX) or file_info.path.endswith(
        CHUNKED_SUFFIX + "/"
    ):
        return FileStateExistsChunked, file_info
    elif file_info.file_type == "dir":
        return FileStateIsDirUnchunked, file_info
    else:
        return FileStateExists, file_info


def _check_file_state(
    oc: owncloud.Client, remote_path: str
) -> Tuple[FileState, Optional[owncloud.FileInfo]]:
    try:
        file_info: owncloud.FileInfo = oc.file_info(remote_path)
        return _check_file_state_from_file_info(file_info)
    except owncloud.owncloud.HTTPResponseError:
        if not remote_path.endswith(CHUNKED_SUFFIX) and not remote_path.endswith(
            CHUNKED_SUFFIX + "/"
        ):
            return _check_file_state(oc, remote_path + CHUNKED_SUFFIX)
    return FileStateDoesNotExist, None


def _download_file(
    oc: owncloud.Client,
    relative_path: str,
    remote_base: str,
    local_base: str,
) -> Optional[bool]:
    if relative_path == "" or relative_path == ".":
        remote_path = remote_base
        local_path = local_base
    else:
        remote_path = os.path.join(remote_base, relative_path)
        local_path = os.path.join(local_base, relative_path)

    file_name = pathlib.Path(remote_path).name
    if not local_path.endswith(file_name):
        local_path = os.path.join(local_path, file_name)

    local_parent_dir = pathlib.Path(local_path).parent
    if not local_parent_dir.exists():
        os.makedirs(local_parent_dir)
    oc.get_file(remote_path=remote_path, local_file=local_path)
    return True


def _download_dir(
    oc: owncloud.Client,
    relative_path: str,
    remote_base: str,
    local_base: str,
    file_info: owncloud.FileInfo,
) -> Optional[bool]:
    for remote_file in oc.list(file_info.path):
        file_state, remote_file_info = _check_file_state_from_file_info(remote_file)
        _download(
            oc=oc,
            relative_path=_remove_commonpath(remote_file_info.path, remote_base),
            remote_base=remote_base,
            local_base=local_base,
            file_state=file_state,
            file_info=remote_file_info,
        )
    return True


def _download(
    oc: owncloud.Client,
    relative_path: str,
    remote_base: str,
    local_base: str,
    file_state: FileState,
    file_info: owncloud.FileInfo,
) -> Optional[bool]:
    if file_state == FileStateIsDirUnchunked:
        _download_dir(
            oc=oc,
            relative_path=_remove_commonpath(file_info.path, remote_base),
            remote_base=remote_base,
            local_base=local_base,
            file_info=file_info,
        )
    elif file_state == FileStateExistsChunked:
        if relative_path == "":
            local_file_path = local_base
        else:
            local_file_path = os.path.join(
                local_base, relative_path.replace(CHUNKED_SUFFIX, "")
            )
        _chunked_download(oc=oc, remote_path=file_info.path, local_path=local_file_path)
    elif file_state == FileStateExists:
        _download_file(
            oc=oc,
            relative_path=_remove_commonpath(file_info.path, remote_base),
            remote_base=remote_base,
            local_base=local_base,
        )
    return True


def download(remote_path: str, local_path: Optional[str] = None) -> Optional[bool]:
    """Download file from remote.

    If the file is chunked it will be reconstructed while downloading. If no local path is given it will be written
    in the current directory. If it exists it will be replaced.

    Args:
        remote_path: Path where the file lies in the shared folder
        local_path: Path where file should downloaded to

    Returns:
        True if successful, else None
    """
    load_dotenv()
    oc = owncloud.Client.from_public_link(
        os.environ[NEXTCLOUD_FOLDER_URI_KEY],
        folder_password=os.environ[NEXTCLOUD_FOLDER_PW_KEY],
    )
    if local_path is None:
        local_path = pathlib.Path(remote_path).name
    if not remote_path.startswith("/"):
        remote_path = "/" + remote_path
    file_state, file_info = _check_file_state(oc=oc, remote_path=remote_path)
    if file_state == FileStateIsDirUnchunked:
        assert file_info  # for mypy
        remote_dir_name = pathlib.Path(file_info.path).name
        if not local_path.endswith(remote_dir_name):
            local_path = os.path.join(local_path, remote_dir_name)
    return _download(
        oc=oc,
        relative_path="",
        remote_base=remote_path,
        local_base=local_path,
        file_state=file_state,
        file_info=file_info,
    )
