# This code is for a project under NDA
# Organization members can read the necessary context for this code in this issue:
# https://github.com/starlinglab/organizing-private/issues/66
#
# The code in this file is copied from this file in a private repo of ours:
# https://github.com/starlinglab/verify-image-sig/blob/main/verify/__init__.py
# The manufacturer has confirmed the code in that file can be released publicly.
#
# The code contains comments, but further context for those comments and the overall
# steps performed can be read in the NOTES.md file from that repo:
# https://github.com/starlinglab/verify-image-sig/blob/main/NOTES.md

import hashlib
from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
import exifread
import exifread.jpeg


class VerificationException(Exception):
    pass


def verify(jpeg_path: str, key_path: str) -> bool:
    """
    Verifies the signature of a "sig66" JPEG file.

    Args:
        jpeg_path: path to JPEG file
        key_path: path to PEM-encoded ECC key file

    Raises:
        sig66.VerificationException if the image is invalid or couldn't be parsed
        Any other exception is unexpected and at a lower level, for example I/O errors

    Returns:
        True if the signature verified, False if not
    """

    # Image file
    file = open(jpeg_path, "rb")

    data = file.read(12)

    if data[:2] != b"\xFF\xD8":
        # Not a JPEG
        raise VerificationException("Not a JPEG file!")

    file.seek(0)

    ##### Metadata #####

    # Get initial offset - the base plus 12
    # Adapted from: https://github.com/ianare/exif-py/blob/3c2113bdd28a48c3520e6baf718eedfc2f8ac04d/exifread/jpeg.py#L117-L124
    # In the steps this is described as:
    #     Find the byte order code (4949) where is the reference position (b’000c’) for following offsets.
    base, fake_exif = exifread.jpeg._get_initial_base(file, data, fake_exif=0)
    file.seek(0)
    data = file.read(base + 4000)
    base = exifread.jpeg._get_base(base, data)
    initial_offset = base + 12

    # Skipping the EXIF step for now, the next step is:
    #     Find Next IFD offset (b’7A51’) which is placed at the end of 0th IFD.
    # Code is adapted from:
    # https://github.com/ianare/exif-py/blob/3c2113bdd28a48c3520e6baf718eedfc2f8ac04d/exifread/__init__.py#L123

    file.seek(0)
    try:
        offset, endian, fake_exif = exifread._determine_type(file)
    except exifread.ExifNotFound:
        raise VerificationException("Image does not seem to contain EXIF data!")
    except exifread.InvalidExif:
        raise VerificationException("Image EXIF data is invalid!")

    endian = chr(exifread.ord_(endian[0]))
    hdr = exifread.ExifHeader(
        file,
        endian,
        offset,
        fake_exif,
        strict=False,
        debug=False,
        detailed=True,
        truncate_tags=True,
    )
    # This is not adapted from process_file
    # This only processes the IFDs we need
    # IFD0 because it contains the ExifOffset tag
    # And IFD1 because we need to know its offset
    ifd0 = hdr._first_ifd()
    hdr.dump_ifd(ifd0, "Image")
    ifd1_offset = hdr._next_ifd(ifd0)

    # Now get the EXIF offset from the tags
    #     Seek EXIF IFD entry (6987) and get the offset for EXIF IFD data (b’0168’).
    exif_offset = hdr.tags.get("Image ExifOffset")
    if not exif_offset:
        raise VerificationException("Image does not seem to contain EXIF data!")
    exif_offset = exif_offset.values[0]

    # Now get metadata bytes
    metadata_start = initial_offset + exif_offset
    metadata_end = ifd1_offset + (initial_offset - 1)
    file.seek(metadata_start)
    metadata = file.read((metadata_end - metadata_start) + 1)

    ##### Image data #####

    # Find Start Of Scan (SOS) which starts image data - indicated by 0xFFDA
    # Search for each of these in turn to find it: FFE1, FFE1, FFE2, FFDB, FFC0, FFC4, FFDA
    file.seek(0)
    file_bytes = file.read()
    file.close()
    start = 0
    for marker in [
        b"\xFF\xE1",
        b"\xFF\xE1",
        b"\xFF\xE2",
        b"\xFF\xDB",
        b"\xFF\xC0",
        b"\xFF\xC4",
        b"\xFF\xDA",
    ]:
        pos = file_bytes.find(marker, start)
        if pos == -1:
            raise VerificationException(
                f"Couldn't find start of image data - couldn't find {marker.hex().upper()}"
            )

        # For the next marker, look past the current one
        start = pos + 2

    # Found SOS (0xFFDA)
    sos_addr = pos
    # Skip past scan header to get to actual start of image data
    sos_length = int.from_bytes(
        file_bytes[sos_addr + 2 : sos_addr + 2 + 2], byteorder="big", signed=False
    )
    image_data_start = sos_addr + sos_length + 2  # +2 to include FFDA bytes

    # Find end of image data - the last FFD9 in the file that isn't part of the signature
    start = image_data_start
    for marker in [b"\xFF\xD9", b"\xFF\xD8", b"\xFF\xD9"]:
        pos = file_bytes.find(marker, start)
        if pos == -1:
            raise VerificationException(
                f"Couldn't find end of image data - couldn't find {marker.hex().upper()}"
            )

        # For the next marker, look past the current one
        start = pos + 2

    image_data_end = pos
    # +2 to include the FFD9 bytes
    image_data = file_bytes[image_data_start : image_data_end + 2]

    # Signature is at the end of the file, immediately following FFD9
    signature = file_bytes[image_data_end + 2 :]

    ### Hash and verify ###

    metadata_hash = hashlib.sha256(metadata).digest()
    image_hash = hashlib.sha256(image_data).digest()
    combination_hash = image_hash + metadata_hash

    # Adapted from signature verification example
    # https://www.pycryptodome.org/en/latest/src/signature/dsa.html

    with open(key_path, "rb") as f:
        key = ECC.import_key(f.read())
    h = SHA256.new(combination_hash)
    verifier = DSS.new(key, "fips-186-3", encoding="der")
    try:
        verifier.verify(h, signature)
        return True
    except ValueError:
        return False
