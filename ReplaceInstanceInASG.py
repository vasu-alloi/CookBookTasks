#!/usr/bin/env python3
"""
Replace Unhealthy EC2 Instances in an Auto Scaling Group (ASG)

This script ensures that only healthy instances are running inside the specified ASG.
It performs the following actions:
  - Logs into AWS using hardcoded credentials (⚠️ testing only, not recommended for production)
  - Lists all instances in the given Auto Scaling Group (ASG)
  - Identifies instances marked as UNHEALTHY
  - Terminates unhealthy instances
  - Waits for the ASG to automatically launch a replacement
  - Confirms that the replacement becomes healthy
  - Logs all actions for auditing

Inputs:
  - ASG_NAME (hardcoded in script)


Safety Checks:
  - Only terminate instances marked as unhealthy
  - Do not decrement ASG desired capacity (so ASG launches a replacement automatically)
  - Wait for replacement to reach healthy state before exit
"""

import boto3
import logging
import sys
import time
from botocore.exceptions import ClientError

# ---------------------------
# Hardcoded AWS Credentials (⚠️ Testing only!)
# ---------------------------
AWS_ACCESS_KEY = "youraccesskey"
AWS_SECRET_KEY = "yoursecretekey"
AWS_REGION = "ap-south-1"

# ---------------------------
# Hardcoded ASG Name
# ---------------------------
ASG_NAME = "JenkinsASGWorkerNode"  # Replace with your ASG name

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


class ASGManager:
    def __init__(self, access_key, secret_key, region):
        """Initialize AWS clients"""
        try:
            self.autoscaling = boto3.client(
                "autoscaling",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            self.ec2 = boto3.client(
                "ec2",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            logging.info(f"Connected to AWS region: {region}")
        except Exception as e:
            logging.error(f"Failed to create AWS clients: {e}")
            sys.exit(1)

    def get_asg_instances(self, asg_name):
        """Get all instances in the ASG"""
        try:
            response = self.autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
            if not response['AutoScalingGroups']:
                logging.error(f"ASG {asg_name} not found.")
                return []
            return response['AutoScalingGroups'][0]['Instances']
        except ClientError as e:
            logging.error(f"Error fetching ASG instances: {e}")
            sys.exit(1)

    def check_instance_health(self, instance_id):
        """Check EC2 instance system health"""
        try:
            response = self.ec2.describe_instance_status(InstanceIds=[instance_id])
            if not response['InstanceStatuses']:
                return "unknown"
            return response['InstanceStatuses'][0]['InstanceStatus']['Status']
        except ClientError as e:
            logging.error(f"Error checking instance status for {instance_id}: {e}")
            return "unknown"

    def replace_unhealthy_instances(self, asg_name):
        """Terminate unhealthy instances and wait for replacement"""
        instances = self.get_asg_instances(asg_name)
        if not instances:
            logging.info("No instances found in ASG.")
            return

        unhealthy_found = False

        for inst in instances:
            instance_id = inst['InstanceId']
            lifecycle_state = inst['LifecycleState']
            health_status = inst['HealthStatus']

            logging.info(f"Checking instance {instance_id} - Health: {health_status}, Lifecycle: {lifecycle_state}")

            if health_status.lower() != 'healthy':
                unhealthy_found = True
                logging.warning(f"Terminating unhealthy instance {instance_id}...")
                try:
                    self.autoscaling.terminate_instance_in_auto_scaling_group(
                        InstanceId=instance_id,
                        ShouldDecrementDesiredCapacity=False  # ensures ASG launches replacement
                    )
                    logging.info(f"Termination initiated for {instance_id}. Waiting for replacement...")
                    if not self.wait_for_healthy_instance(asg_name):
                        logging.error("Replacement instance did not become healthy in time.")
                        sys.exit(1)
                except ClientError as e:
                    logging.error(f"Error terminating instance {instance_id}: {e}")
                    sys.exit(1)

        if not unhealthy_found:
            logging.info("✅ All instances in ASG are already healthy.")

    def wait_for_healthy_instance(self, asg_name, timeout=600, interval=15):
        """Wait for new instance to become healthy"""
        logging.info("Waiting for replacement instance to become healthy...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            instances = self.get_asg_instances(asg_name)
            all_healthy = all(inst['HealthStatus'].lower() == 'healthy' for inst in instances)

            if all_healthy:
                logging.info("✅ All instances in ASG are healthy now.")
                return True

            for inst in instances:
                logging.info(f"Instance {inst['InstanceId']} is {inst['HealthStatus']} ({inst['LifecycleState']})")

            time.sleep(interval)

        logging.error("⏳ Timeout reached while waiting for healthy replacement instance.")
        return False


def main():
    manager = ASGManager(AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION)
    manager.replace_unhealthy_instances(ASG_NAME)


if __name__ == "__main__":
    main()
