import pathlib
import os

import uuid
import numpy as np
import owncloud
import pytest
from dotenv import load_dotenv

from nephelai import download, upload
from nephelai.api import NEXTCLOUD_FOLDER_PW_KEY, NEXTCLOUD_FOLDER_URI_KEY

uuid_dir = str(uuid.uuid4())
remote_tmp_dir_base = "pytest"
remote_tmpdir = f"{remote_tmp_dir_base}/remote_tmpdir/{uuid_dir}"


@pytest.fixture(autouse=True)
def cleanup():
    # before test
    yield  # run test
    # after test
    load_dotenv()
    oc = owncloud.Client.from_public_link(
        os.environ[NEXTCLOUD_FOLDER_URI_KEY],
        folder_password=os.environ[NEXTCLOUD_FOLDER_PW_KEY],
    )
    oc.delete(remote_tmp_dir_base)


@pytest.mark.parametrize("chunk_size", ["1KiB", "100MiB"])
def test_upload_and_download_folder(chunk_size, tmpdir):
    resources_path = "tests/resources/"
    assert upload(resources_path, remote_tmpdir, chunk_size=chunk_size)
    dl_path = tmpdir.mkdir("tests")
    assert download(remote_tmpdir, str(dl_path))
    dl_path_folder = dl_path.join(uuid_dir)

    assert len(dl_path_folder.listdir()) == 2

    with open(
        dl_path_folder.join("subfolder").join("testfile.txt"), "r"
    ) as file_handle:
        res = file_handle.read()
        assert res == "simple testfile\n"
    assert len(np.load(str(dl_path_folder.join("mymatrix.npy")))) == 1000


@pytest.mark.parametrize("chunk_size", ["1KiB", "100MiB"])
@pytest.mark.parametrize("upload_to_dir", [True, False])
def test_upload_and_download_file(chunk_size, upload_to_dir, tmpdir):
    remote_file_path = remote_tmpdir + "/mymatrix.npy"
    remote_file_path if not upload_to_dir else remote_tmpdir
    resources_file_path = "tests/resources/mymatrix.npy"
    assert upload(resources_file_path, remote_file_path, chunk_size=chunk_size)
    dl_path = tmpdir.mkdir("tests").join("mymatrix.npy")
    assert download(remote_file_path, str(dl_path))
    assert len(np.load(str(dl_path))) == 1000
