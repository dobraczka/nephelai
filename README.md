<p align="center">
<img src="https://github.com/dobraczka/nephelai/raw/main/docs/assets/logo.png" alt="nephelai logo", width=200/>
<h2 align="center">nephelai</h2>
</p>

<p align="center">
<a href="https://github.com/dobraczka/nephelai/actions/workflows/main.yml"><img alt="Actions Status" src="https://github.com/dobraczka/nephelai/actions/workflows/main.yml/badge.svg?branch=main"></a>
<a href='https://nephelai.readthedocs.io/en/latest/?badge=latest'><img src='https://readthedocs.org/projects/nephelai/badge/?version=latest' alt='Documentation Status' /></a>
<a href="https://pypi.org/project/nephelai"/><img alt="Stable python versions" src="https://img.shields.io/pypi/pyversions/nephelai"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

A helper library to upload/download files to/from a password-protected shared nextcloud folder. The link and password are read from your `.env` to enable project-specific shared folders.
Because Nextcloud does not enable chunked uploads for shared folders and your files can hit the size limit, your files are uploaded in chunks if needed and reconstructed after download.

Usage
=====
Create a `.env` file in your project root.
Remember to add this file to your `.gitignore` and always keep it secure to keep your secrets!
Your `.env` should contain:
```bash
NEXTCLOUD_FOLDER_URI="uri_of_the_shared_folder"
NEXTCLOUD_FOLDER_PW="pw_of_the_folder"
```
Then you can interact with the folder in a variety of ways.
Alternatively, you can set this environment variables yourself with your preferred method.

Via CLI:
--------
```bash
nephelai upload mytestfile.txt anextcloud/path/thatwillbecreatedifneeded/
nephelai download anextcloud/path/thatwillbecreatedifneeded/mytestfile.txt
```
You can also upload folders including the file structure:
```bash
tests/resources
├── mymatrix.npy
└── subfolder
    └── testfile.txt
```
Using the `upload-with-fs` command:
```bash
nephelai upload-with-fs tests/resources
```

Which is just syntactic sugar for:

```bash
nephelai upload tests/resources tests/resources
```

Downloading can be done accordingly:
```bash
nephelai download tests
```
Which will download it to your current directory. You can also specify the download path:

```bash
nephelai download tests --local-path /tmp/
```
This download the folder as:
```bash
/tmp/tests
└── resources
    ├── mymatrix.npy
    └── subfolder
        └── testfile.txt
```

You can get help for each command via the `--help` flag.

Via Python:
----------
```python
from nephelai import upload, download

upload("tests/resources", "tests/resources")
file_dl_path = "/tmp/mymatrix.npy"
download("tests/resources/mymatrix.npy",file_dl_path)

import numpy as np

mymatrix = np.load(file_dl_path)
```

Installation
============

`pip install nephelai`
