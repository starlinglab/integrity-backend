from .asset_helper import AssetHelper
from .claim import Claim
from .claim_tool import ClaimTool
from .filecoin import Filecoin

import csv
import logging
import os
import shutil
import time
import tempfile
import zipfile
from PIL import Image, ExifTags

_asset_helper = AssetHelper()
_claim = Claim()
_claim_tool = ClaimTool()
_filecoin = Filecoin()
_logger = logging.getLogger(__name__)


class Actions:
    """Actions for processing assets."""

    def create(self, asset_fullpath, jwt_payload, meta):
        """Process asset with create action.
        A new asset file is generated in the create-output folder with an original creation claim.

        Args:
            asset_fullpath: the local path to the asset file
            jwt_payload: a JWT payload containing metadata
            meta: dictionary with the 'meta' section of the incoming multipart request

        Returns:
            the local path to the asset file in the internal directory

        Raises:
            Exception if errors are encountered during processing
        """
        # Create temporary files to work with.
        tmp_asset_file = _asset_helper.get_tmp_file_fullpath(".jpg")
        tmp_claim_file = _asset_helper.get_tmp_file_fullpath(".json")

        # Inject create claim and read back from file.
        claim = _claim.generate_create(jwt_payload, meta)
        time.sleep(1)
        _logger.info("File size: %s", os.path.getsize(asset_fullpath))
        shutil.copy2(asset_fullpath, tmp_asset_file)
        _claim_tool.run_claim_inject(claim, tmp_asset_file, None)
        _claim_tool.run_claim_dump(tmp_asset_file, tmp_claim_file)

        # Copy the C2PA-injected asset to both the internal and shared asset directories.
        internal_asset_file = _asset_helper.get_internal_file_fullpath(tmp_asset_file)
        shutil.move(tmp_asset_file, internal_asset_file)
        subfolder = jwt_payload.get("author", {}).get("name")
        shutil.copy2(internal_asset_file, _asset_helper.get_assets_create_output(subfolder))
        _logger.info("New asset file added: %s", internal_asset_file)
        internal_claim_file = _asset_helper.get_internal_claim_fullpath(
            internal_asset_file
        )
        shutil.move(tmp_claim_file, internal_claim_file)
        _logger.info(
            "New claim file added to the internal claims directory: %s",
            internal_claim_file,
        )
        return internal_asset_file

    def create_proofmode(self, asset_fullpath, jwt_payload):
        """Process proofmode bundled asset with create action.
        A new asset file is generated in the create-proofmode-output folder with an original creation claim.

        Args:
            asset_fullpath: the local path to the proofmode bundled asset file
            jwt_payload: a JWT payload containing metadata

        Returns:
            the local path to the asset file in the internal directory

        Raises:
            Exception if errors are encountered during processing
        """
        # Create temporary files to work with.
        tmp_asset_file = _asset_helper.get_tmp_file_fullpath(".jpg")
        tmp_claim_file = _asset_helper.get_tmp_file_fullpath(".json")

        # Unzip bundle, store asset file, and create dictionary for claim creation.
        with tempfile.TemporaryDirectory() as tmp_unzip_folder:
            with zipfile.ZipFile(asset_fullpath, 'r') as zip_ref:
                zip_ref.extractall(tmp_unzip_folder)
                for file in os.listdir(tmp_unzip_folder):
                    if file.endswith(".jpg"):
                        shutil.copy2(os.path.join(tmp_unzip_folder, file), tmp_asset_file)
                        img = Image.open(os.path.join(tmp_unzip_folder, file))
                        exif_data = img._getexif()
                        exif_dict = {}
                        for (k,v) in exif_data.items():
                            if k in ExifTags.TAGS:
                                exif_dict[ExifTags.TAGS.get(k)]=v

                        gpsinfo = {}
                        for key in exif_dict['GPSInfo'].keys():
                            decode = ExifTags.GPSTAGS.get(key,key)
                            gpsinfo[decode] = exif_dict['GPSInfo'][key]

                    if file.endswith(".csv"):
                        csv_reader=csv.DictReader(open(os.path.join(tmp_unzip_folder,file)))
                        meta_csv = next(csv_reader)

        info = []
        
        (lat, lon) = self._get_lat_lon(exif_dict)
        info = [
          {"name": "Last Known GPS Latitude", "value": lat},
          {"name": "Last Known GPS Longitude", "value": lon}
        ]
        meta_proofmode = {"information": info}
        
        # Inject create claim and read back from file.
        claim = _claim.generate_create_proofmode(jwt_payload, meta_proofmode)
        _claim_tool.run_claim_inject(claim, tmp_asset_file, None)
        _claim_tool.run_claim_dump(tmp_asset_file, tmp_claim_file)

        # Copy the C2PA-injected asset to both the internal and shared asset directories.
        internal_asset_file = _asset_helper.get_internal_file_fullpath(tmp_asset_file)
        shutil.move(tmp_asset_file, internal_asset_file)
        subfolder = jwt_payload.get("author", {}).get("name")
        shutil.copy2(internal_asset_file, _asset_helper.get_assets_create_proofmode_output(subfolder))
        _logger.info("New asset file added: %s", internal_asset_file)
        internal_claim_file = _asset_helper.get_internal_claim_fullpath(
            internal_asset_file
        )
        shutil.move(tmp_claim_file, internal_claim_file)
        _logger.info(
            "New claim file added to the internal claims directory: %s",
            internal_claim_file,
        )
        return internal_asset_file

    def add(self, asset_fullpath):
        """Process asset with add action.
        The provided asset file is added to the asset management system and renamed to its internal identifier in the add-output folder.

        Args:
            asset_fullpath: the local path to the asset file

        Returns:
            the local path to the asset file in the internal directory
        """
        return self._add(asset_fullpath, _asset_helper.get_assets_add_output())

    def update(self, asset_fullpath):
        """Process asset with update action.
        A new asset file is generated in the update-output folder with a claim that links it to a parent asset identified by its filename.

        Args:
            asset_fullpath: the local path to the asset file

        Returns:
            the local path to the asset file in the internal directory
        """
        return self._update(
            asset_fullpath,
            _claim.generate_update(),
            _asset_helper.get_assets_update_output(),
        )

    def store(self, asset_fullpath):
        """Process asset with store action.
        The provided asset stored on decentralized storage, then a new asset file is generated in the store-output folder with a storage claim.

        Args:
            asset_fullpath: the local path to the asset file

        Returns:
            the local path to the asset file in the internal directory
        """
        # Add uploaded asset to the internal directory.
        added_asset = self._add(asset_fullpath, None)

        # Store asset to IPFS and Filecoin.
        ipfs_cid = _filecoin.upload(added_asset)
        _logger.info("Asset file uploaded to IPFS with CID: %s", ipfs_cid)

        return self._update(
            added_asset,
            _claim.generate_store(ipfs_cid),
            _asset_helper.get_assets_store_output(),
        )

    def _add(self, asset_fullpath, output_dir):
        # Create temporary files to work with.
        tmp_asset_file = _asset_helper.get_tmp_file_fullpath(".jpg")
        time.sleep(1)
        _logger.info("File size: %s", os.path.getsize(asset_fullpath))
        shutil.copy2(asset_fullpath, tmp_asset_file)

        # Copy asset to both the internal and shared asset directories.
        internal_asset_file = _asset_helper.get_internal_file_fullpath(tmp_asset_file)
        shutil.move(tmp_asset_file, internal_asset_file)
        if output_dir is not None:
            shutil.copy2(internal_asset_file, output_dir)
        _logger.info("New asset file added: %s", internal_asset_file)

        return internal_asset_file

    def _update(self, asset_fullpath, claim, output_dir):
        # Create temporary files to work with.
        tmp_asset_file = _asset_helper.get_tmp_file_fullpath(".jpg")
        tmp_claim_file = _asset_helper.get_tmp_file_fullpath(".json")

        # Parse file name to get internal name for parent file.
        file_name, file_extension = os.path.splitext(os.path.basename(asset_fullpath))
        parent_file = os.path.join(
            _asset_helper.get_assets_internal(),
            file_name.partition("_")[0].partition("-")[0] + file_extension,
        )

        # Inject update claim and read back from file.
        time.sleep(1)
        _logger.info("File size: %s", os.path.getsize(asset_fullpath))
        shutil.copy2(asset_fullpath, tmp_asset_file)
        _logger.info("Searching for parent file: %s", parent_file)
        if not os.path.isfile(parent_file):
            raise Exception(f"Expected {parent_file} to be a file, but it isn't")

        _logger.info("_update() action found parent file for asset: %s", parent_file)
        _claim_tool.run_claim_inject(claim, tmp_asset_file, parent_file)
        _claim_tool.run_claim_dump(tmp_asset_file, tmp_claim_file)
        # Copy the C2PA-injected asset to both the internal and shared asset directories.
        internal_asset_file = _asset_helper.get_internal_file_fullpath(tmp_asset_file)
        shutil.move(tmp_asset_file, internal_asset_file)
        if output_dir is not None:
            shutil.copy2(internal_asset_file, output_dir)
        _logger.info("New asset file added: %s", internal_asset_file)
        internal_claim_file = _asset_helper.get_internal_claim_fullpath(
            internal_asset_file
        )
        shutil.move(tmp_claim_file, internal_claim_file)
        _logger.info(
            "New claim file added to the internal claims directory: %s",
            internal_claim_file,
        )
        return internal_asset_file

    def _convert_to_degress(self, value):
        """Helper function to convert the GPS coordinates stored in the EXIF to degress in float format"""
        d0 = value[0][0]
        d1 = value[0][1]
        d = float(d0) / float(d1)

        m0 = value[1][0]
        m1 = value[1][1]
        m = float(m0) / float(m1)

        s0 = value[2][0]
        s1 = value[2][1]
        s = float(s0) / float(s1)

        return d + (m / 60.0) + (s / 3600.0)

    def _get_lat_lon(self, exif_data):
        """Returns the latitude and longitude, if available, from the provided exif_data (obtained through get_exif_data above)"""
        lat = None
        lon = None

        if "GPSInfo" in exif_data:		
            gps_info = exif_data["GPSInfo"]

            gps_latitude = gps_info.get("GPSLatitude")
            gps_latitude_ref = gps_info.get(gps_info, 'GPSLatitudeRef')
            gps_longitude = gps_info.get(gps_info, 'GPSLongitude')
            gps_longitude_ref = gps_info.get(gps_info, 'GPSLongitudeRef')

            if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
                lat = self._convert_to_degress(gps_latitude)
                if gps_latitude_ref != "N":                     
                    lat = 0 - lat

                lon = self._convert_to_degress(gps_longitude)
                if gps_longitude_ref != "E":
                    lon = 0 - lon

        return lat, lon