#!/usr/bin/env python3
"""
EBS Volume Expansion Script 
This script increases the size of an EBS volume.
"""

import boto3
import sys
import time
import logging
from botocore.exceptions import ClientError

# --------------------------
# Logging Configuration
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# --------------------------
# HARDCODED CONFIG (for testing only!)
# --------------------------
AWS_ACCESS_KEY_ID = "youraccesskey"
AWS_SECRET_ACCESS_KEY = "yoursecretekey"
AWS_REGION = "ap-south-1"   # Example: Mumbai region
VOLUME_ID = "vol-055a179707394c2d6"   # Example volume
NEW_SIZE = 5  # GiB

class EBSVolumeExpander:
    def __init__(self, access_key, secret_key, region):
        self.ec2_client = boto3.client(
            "ec2",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,   # ✅ Fixed parameter name
            region_name=region
        )

    def get_volume(self, volume_id):
        """Fetch EBS volume details"""
        try:
            resp = self.ec2_client.describe_volumes(VolumeIds=[volume_id])
            vol = resp["Volumes"][0]
            logging.info(f"Volume {volume_id} - Current Size: {vol['Size']} GiB, State: {vol['State']}")
            return vol
        except ClientError as e:
            logging.error(f"Error fetching volume: {e}")
            return None

    def expand_volume(self, volume_id, new_size):
        """Modify EBS volume size"""
        try:
            self.ec2_client.modify_volume(VolumeId=volume_id, Size=new_size)
            logging.info(f"Expansion initiated: {volume_id} → {new_size} GiB")
            return True
        except ClientError as e:
            logging.error(f"Error expanding volume: {e}")
            return False

    def verify_expansion(self, volume_id, new_size, timeout=300):
        """Verify that expansion succeeded"""
        logging.info("Verifying expansion...")
        start = time.time()
        while time.time() - start < timeout:
            vol = self.get_volume(volume_id)
            if vol and vol["Size"] >= new_size:
                logging.info(f"SUCCESS: Volume {volume_id} resized to {vol['Size']} GiB")
                return True
            time.sleep(10)
        logging.warning(f"Timeout: Could not verify expansion of {volume_id}")
        return False

    def run(self, volume_id, new_size):
        """Main workflow"""
        volume = self.get_volume(volume_id)
        if not volume:
            return False

        current_size = volume["Size"]
        if new_size <= current_size:
            logging.error(f"Invalid request: New size {new_size} GiB must be larger than current {current_size} GiB")
            return False

        if not self.expand_volume(volume_id, new_size):
            return False

        return self.verify_expansion(volume_id, new_size)


def main():
    expander = EBSVolumeExpander(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION)
    success = expander.run(VOLUME_ID, NEW_SIZE)

    if success:
        logging.info("Next steps (on instance):")
        logging.info("  - Use `lsblk` to see new size")
        logging.info("  - Grow filesystem: e.g., `sudo resize2fs /dev/xvdf` (for ext4)")
        sys.exit(0)
    else:
        logging.error("Volume expansion failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
