#!/usr/bin/env python3
"""
EBS Snapshot Cleanup Script

This script deletes EBS snapshots older than a specified retention period.
It performs the following actions:
  - Logs into AWS using hardcoded credentials (for testing only)
  - Lists all snapshots owned by the account
  - Deletes snapshots older than `RETENTION_DAYS`
  - Logs actions and deleted snapshots for auditing

Safety Checks:
  - Only deletes snapshots older than retention period
  - Logs all deletions
"""

import boto3
import datetime
import logging
import sys
from botocore.exceptions import ClientError

# ---------------------------
# Hardcoded AWS Credentials (Testing only!)
# ---------------------------
AWS_ACCESS_KEY = "youraccesskey"
AWS_SECRET_KEY = "yoursecretekey"
AWS_REGION = "ap-south-1"

# ---------------------------
# Hardcoded retention period
# ---------------------------
RETENTION_DAYS = 120  # Snapshots older than 30 days will be deleted

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

class EBSSnapshotCleaner:
    def __init__(self, access_key, secret_key, region):
        """Initialize AWS EC2 client"""
        self.ec2 = boto3.client(
            "ec2",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

    def delete_old_snapshots(self, retention_days):
        """Delete snapshots older than retention_days"""
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=retention_days)
        logging.info(f"Deleting snapshots older than {retention_days} days (before {cutoff_date})")

        try:
            # List snapshots owned by the account
            snapshots = self.ec2.describe_snapshots(OwnerIds=['self'])['Snapshots']
            deleted_snapshots = []

            for snap in snapshots:
                start_time = snap['StartTime'].replace(tzinfo=None)  # make naive for comparison
                snapshot_id = snap['SnapshotId']

                if start_time < cutoff_date:
                    logging.info(f"Deleting snapshot {snapshot_id}, created on {start_time}")
                    self.ec2.delete_snapshot(SnapshotId=snapshot_id)
                    deleted_snapshots.append(snapshot_id)

            if deleted_snapshots:
                logging.info(f"✅ Deleted snapshots: {', '.join(deleted_snapshots)}")
            else:
                logging.info("No snapshots older than retention period found.")

            return deleted_snapshots

        except ClientError as e:
            logging.error(f"Error deleting snapshots: {e}")
            return []


def main():
    cleaner = EBSSnapshotCleaner(AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION)
    cleaner.delete_old_snapshots(RETENTION_DAYS)


if __name__ == "__main__":
    main()
