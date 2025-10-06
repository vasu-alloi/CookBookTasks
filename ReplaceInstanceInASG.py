#!/usr/bin/env python3
"""
Replace Unhealthy EC2 Instances in an Auto Scaling Group

This script performs the following actions:
  - Logs into AWS using hardcoded credentials (for testing only)
  - Checks all instances in the given ASG
  - Terminates any unhealthy instance
  - ASG automatically launches a replacement instance
  - Waits for the replacement instance to become healthy
  - Logs all actions for auditing

Inputs:
  - ASG_NAME (hardcoded or provided as input)


Safety Checks:
  - Only terminate instances marked as unhealthy
  - Wait for replacement to become healthy before exiting
"""

import boto3
import logging
import sys
import time
from botocore.exceptions import ClientError

# ---------------------------
# Hardcoded AWS Credentials ( Testing only!)
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

    def get_asg_instances(self, asg_name):
        """Get all instances in the ASG"""
        try:
            response = self.autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
            if not response['AutoScalingGroups']:
                logging.error(f"ASG {asg_name} not found.")
                return []
            instances = response['AutoScalingGroups'][0]['Instances']
            return instances
        except ClientError as e:
            logging.error(f"Error fetching ASG instances: {e}")
            return []

    def check_instance_health(self, instance_id):
        """Check EC2 instance health status"""
        try:
            response = self.ec2.describe_instance_status(InstanceIds=[instance_id])
            if not response['InstanceStatuses']:
                return "unknown"
            status = response['InstanceStatuses'][0]['InstanceStatus']['Status']
            return status
        except ClientError as e:
            logging.error(f"Error checking instance status: {e}")
            return "unknown"

    def replace_unhealthy_instances(self, asg_name):
        """Terminate unhealthy instances and wait for healthy replacement"""
        instances = self.get_asg_instances(asg_name)
        if not instances:
            logging.info("No instances found in ASG.")
            return

        for inst in instances:
            instance_id = inst['InstanceId']
            lifecycle_state = inst['LifecycleState']
            health_status = inst['HealthStatus']

            logging.info(f"Checking instance {instance_id} - Health: {health_status}, Lifecycle: {lifecycle_state}")

            if health_status.lower() != 'healthy':
                logging.warning(f"Terminating unhealthy instance {instance_id}...")
                try:
                    self.autoscaling.terminate_instance_in_auto_scaling_group(
                        InstanceId=instance_id,
                        ShouldDecrementDesiredCapacity=False
                    )
                    logging.info(f"Termination initiated for {instance_id}. Waiting for replacement...")
                    self.wait_for_healthy_instance(asg_name)
                except ClientError as e:
                    logging.error(f"Error terminating instance: {e}")

    def wait_for_healthy_instance(self, asg_name, timeout=600, interval=15):
        """Wait for new instance to become healthy"""
        logging.info("Waiting for replacement instance to become healthy...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            instances = self.get_asg_instances(asg_name)
            all_healthy = True
            for inst in instances:
                if inst['HealthStatus'].lower() != 'healthy':
                    all_healthy = False
                    logging.info(f"Instance {inst['InstanceId']} is still unhealthy ({inst['HealthStatus']})")
                    break
            if all_healthy:
                logging.info("All instances in ASG are healthy.")
                return True
            time.sleep(interval)

        logging.warning("Timeout waiting for healthy instances.")
        return False

def main():
    manager = ASGManager(AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION)
    manager.replace_unhealthy_instances(ASG_NAME)


if __name__ == "__main__":
    main()
