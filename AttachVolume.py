# Python example
#!/usr/bin/env python3
"""
EBS Volume Attachment Script
Attaches an EBS volume to an EC2 instance
"""
import boto3
import sys
import time
import logging
from botocore.exceptions import ClientError

# --------------------------
# Hardcoded Configuration (TESTING ONLY)
# --------------------------
AWS_ACCESS_KEY_ID = "yourAccessKey"
AWS_SECRET_ACCESS_KEY = "yourSecreteKey"
AWS_REGION = "ap-south-1"

EBS_VOLUME_ID = "vol-055a179707394c2d6"
EC2_INSTANCE_ID = "i-0456f74a1c5c313c4"
DEVICE_NAME = "/dev/sdf"

# --------------------------
# Logging Configuration
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


class EBSVolumeAttacher:
    def __init__(self, region=None, access_key=None, secret_key=None):
        """Initialize EC2 client and resource with explicit credentials"""
        self.ec2_client = boto3.client(
            "ec2",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        self.ec2_resource = boto3.resource(
            "ec2",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        logging.info(f"Connected to AWS region: {region}")

    def get_volume(self, volume_id):
        """Fetch EBS volume details"""
        try:
            vol = self.ec2_client.describe_volumes(VolumeIds=[volume_id])["Volumes"][0]
            logging.info(f"Volume {volume_id} found (State: {vol['State']}, AZ: {vol['AvailabilityZone']})")
            return vol
        except ClientError as e:
            logging.error(f"Error fetching volume: {e}")
            return None

    def get_instance(self, instance_id):
        """Fetch EC2 instance details"""
        try:
            inst = self.ec2_client.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
            logging.info(f"Instance {instance_id} found (State: {inst['State']['Name']}, AZ: {inst['Placement']['AvailabilityZone']})")
            return inst
        except ClientError as e:
            logging.error(f"Error fetching instance: {e}")
            return None

    def verify_prereqs(self, volume, instance):
        """Check volume, instance, and AZ compatibility"""
        if volume["State"] != "available":
            logging.error(f"Volume {volume['VolumeId']} is not available (State: {volume['State']})")
            return False

        if instance["State"]["Name"] != "running":
            logging.error(f"Instance {instance['InstanceId']} is not running (State: {instance['State']['Name']})")
            return False

        if volume["AvailabilityZone"] != instance["Placement"]["AvailabilityZone"]:
            logging.error(f"AZ mismatch! Volume in {volume['AvailabilityZone']}, Instance in {instance['Placement']['AvailabilityZone']}")
            return False

        logging.info("All prerequisite checks passed")
        return True

    def attach(self, volume_id, instance_id, device_name):
        """Attach volume to instance"""
        try:
            self.ec2_client.attach_volume(
                VolumeId=volume_id,
                InstanceId=instance_id,
                Device=device_name
            )
            logging.info(f"Attachment of {volume_id} to {instance_id} initiated at {device_name}")
            return True
        except ClientError as e:
            logging.error(f"Error attaching volume: {e}")
            return False

    def verify_attachment(self, volume_id, instance_id, device_name, timeout=120):
        """Verify volume attachment"""
        logging.info("Verifying attachment...")
        start = time.time()
        while time.time() - start < timeout:
            vol = self.get_volume(volume_id)
            if vol and vol["State"] == "in-use":
                for att in vol.get("Attachments", []):
                    if att["InstanceId"] == instance_id and att["Device"] == device_name and att["State"] == "attached":
                        logging.info(f"SUCCESS: Volume {volume_id} attached to {instance_id} at {device_name}")
                        return True
            time.sleep(5)
        logging.warning(f"Timeout: Could not verify attachment of {volume_id}")
        return False

    def run(self, volume_id, instance_id, device_name):
        """Main workflow"""
        volume = self.get_volume(volume_id)
        instance = self.get_instance(instance_id)

        if not volume or not instance:
            return False

        if not self.verify_prereqs(volume, instance):
            return False

        if not self.attach(volume_id, instance_id, device_name):
            return False

        return self.verify_attachment(volume_id, instance_id, device_name)


def main():
    attacher = EBSVolumeAttacher(
        region=AWS_REGION,
        access_key=AWS_ACCESS_KEY_ID,
        secret_key=AWS_SECRET_ACCESS_KEY
    )
    success = attacher.run(EBS_VOLUME_ID, EC2_INSTANCE_ID, DEVICE_NAME)

    if success:
        logging.info("Next steps (on instance):")
        logging.info(f"  - Check: lsblk")
        logging.info(f"  - Format if new: sudo mkfs -t ext4 {DEVICE_NAME}")
        logging.info(f"  - Mount: sudo mount {DEVICE_NAME} /mnt/data")
        sys.exit(0)
    else:
        logging.error("Volume attachment failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
