import os.path
import shutil
import zipfile


def make(filepaths: list[str], out_file: str, flat=False):
    """Makes a zip file containing the given list of files.

    Files are stored uncompressed.

    Args:
        filepaths: list of paths to files to include in zip
        out_file: full path to output zip file
        flat: if True then the directory structure indicated by the filepaths will
              not be maintained, and all files will be stored in the root of the zip.

    Raises:
        any issues with file i/o
    """

    with zipfile.ZipFile(out_file, "w") as zipf:
        for filepath in filepaths:
            if flat:
                arcname = os.path.basename(filepath)
            else:
                arcname = filepath
            zipf.write(filepath, arcname)


def extract_file(zip_path, file_path, out_path):
    """Extracts a file from an existing ZIP.

    Args:
        zip_path: path to the ZIP file
        file_path: the path of the file in the ZIP archive
        out_path: the path the file will be written to

    Raises:
        any file i/o exceptions
    """

    with zipfile.ZipFile(zip_path, "r") as zipf:
        with zipf.open(file_path) as zippedf:
            with open(out_path, "wb") as f:
                shutil.copyfileobj(zippedf, f)


def append(zip_path, file_path, archive_path):
    """Append a file to an existing ZIP.

    The file is stored uncompressed.

    Args:
        zip_path: path to the ZIP file
        file_path: path to file on disk
        archive_path: full path of the file inside the ZIP archive

    Raises:
        any file i/o exceptions
    """

    with zipfile.ZipFile(zip_path, "a") as zipf:
        zipf.write(file_path, arcname=archive_path)


def listing(zip_path):
    """Get list of all the filepaths in a ZIP.

    Args:
        zip_path: path to the ZIP file

    Returns: a list of strings, the ZIP member filepaths

    Raises:
        any file i/o exceptions
    """

    with zipfile.ZipFile(zip_path, "r") as zipf:
        return zipf.namelist()
