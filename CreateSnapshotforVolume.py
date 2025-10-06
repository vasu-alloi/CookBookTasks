#!/usr/bin/env python3
"""
EBS Volume Snapshot Creator

This script creates a snapshot of a specified EBS volume.
It performs the following actions:
  - Logs into AWS using hardcoded credentials (for testing only).
  - Creates a snapshot of the given EBS volume.
  - Tags the snapshot with a timestamp for easy identification.
  - Waits for the snapshot to complete.
  - Logs actions and errors for audit purposes.

Inputs:
  - volume_id (hardcoded in script)

IAM Permissions Required:
  - ec2:CreateSnapshot
  - ec2:DescribeSnapshots

Safety Checks:
  - Snapshot is tagged with current timestamp for traceability.
"""

import boto3
import datetime
import logging
import sys
from botocore.exceptions import ClientError

# ---------------------------
# Hardcoded AWS Credentials (⚠️ Testing only!)
# ---------------------------
AWS_ACCESS_KEY = "youraccesskey"
AWS_SECRET_KEY = "yoursecretekey"
AWS_REGION = "ap-south-1"

# ---------------------------
# Hardcoded Volume ID (EBS)
# ---------------------------
VOLUME_ID = "vol-055a179707394c2d6"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

class EBSSnapshotManager:
    def __init__(self, access_key, secret_key, region):
        """Initialize AWS EC2 client"""
        self.ec2 = boto3.client(
            "ec2",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

    def create_snapshot(self, volume_id):
        """Create snapshot of given EBS volume"""
        try:
            timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H-%M-%S")
            description = f"Snapshot of {volume_id} taken at {timestamp}"

            logging.info(f"Creating snapshot for volume {volume_id}...")
            response = self.ec2.create_snapshot(
                VolumeId=volume_id,
                Description=description,
                TagSpecifications=[
                    {
                        "ResourceType": "snapshot",
                        "Tags": [
                            {"Key": "Name", "Value": f"Snapshot-{volume_id}-{timestamp}"},
                            {"Key": "CreatedAt", "Value": timestamp}
                        ]
                    }
                ]
            )

            snapshot_id = response["SnapshotId"]
            logging.info(f"Snapshot {snapshot_id} creation started.")

            # Wait for completion
            self._wait_for_snapshot(snapshot_id)

            logging.info(f"✅ Snapshot {snapshot_id} completed successfully.")
            return snapshot_id

        except ClientError as e:
            logging.error(f"Error creating snapshot: {e}")
            return None

    def _wait_for_snapshot(self, snapshot_id):
        """Wait until snapshot is completed"""
        logging.info(f"Waiting for snapshot {snapshot_id} to complete...")
        waiter = self.ec2.get_waiter("snapshot_completed")
        waiter.wait(SnapshotIds=[snapshot_id])


def main():
    manager = EBSSnapshotManager(AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION)
    snapshot_id = manager.create_snapshot(VOLUME_ID)

    if snapshot_id:
        logging.info(f"Snapshot created successfully: {snapshot_id}")
    else:
        logging.error("Snapshot creation failed.")


if __name__ == "__main__":
    main()
