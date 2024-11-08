from modules.common import exponential_backoff

def list_auto_scaling_groups(session):
    asg_data = []
    try:
        asg_client = session.client('autoscaling')
        ec2_client = session.client('ec2')
        elb_client = session.client('elbv2')
        paginator = asg_client.get_paginator('describe_auto_scaling_groups')
        response_iterator = paginator.paginate()

        for response in response_iterator:
            for asg in response['AutoScalingGroups']:
                name = asg['AutoScalingGroupName']
                launch_template = "-"
                if 'LaunchTemplate' in asg:
                    lt = asg['LaunchTemplate']
                    launch_template = f"{lt['LaunchTemplateName']} (Version: {lt['Version']})"
                elif 'LaunchConfigurationName' in asg:
                    launch_template = asg['LaunchConfigurationName']

                instances_details = []
                instance_types = []
                ami_ids = []
                security_groups_set = set()
                for instance in asg['Instances']:
                    instance_id = instance['InstanceId']
                    try:
                        instance_info = exponential_backoff(ec2_client.describe_instances, InstanceIds=[instance_id])
                        if instance_info['Reservations'] and instance_info['Reservations'][0]['Instances']:
                            instance_type = instance_info['Reservations'][0]['Instances'][0]['InstanceType']
                            ami_id = instance_info['Reservations'][0]['Instances'][0]['ImageId']
                            security_groups = [sg['GroupId'] for sg in instance_info['Reservations'][0]['Instances'][0]['SecurityGroups']]
                            security_groups_set.update(security_groups)
                            instances_details.append(instance_id)
                            instance_types.append(instance_type)
                            ami_ids.append(ami_id)
                    except Exception as e:
                        print(f"Error retrieving instance info for {instance_id}: {e}")

                instances = ', '.join(instances_details)
                instance_types_str = ', '.join(instance_types)
                ami_ids_str = ', '.join(ami_ids)
                security_groups_str = ', '.join(security_groups_set)
                desired_capacity = asg['DesiredCapacity']
                min_size = asg['MinSize']
                max_size = asg['MaxSize']
                availability_zones = ', '.join(asg['AvailabilityZones'])

                # Load Balancer Target Groups
                target_groups = []
                for tg_arn in asg.get('TargetGroupARNs', []):
                    try:
                        tg_info = exponential_backoff(elb_client.describe_target_groups, TargetGroupArns=[tg_arn])
                        if tg_info['TargetGroups']:
                            tg_name = tg_info['TargetGroups'][0]['TargetGroupName']
                            target_groups.append(tg_name)
                    except Exception as e:
                        print(f"Error retrieving target group info for {tg_arn}: {e}")
                target_groups_str = ', '.join(target_groups)

                # Subnet IDs
                subnet_ids = ', '.join(asg.get('VPCZoneIdentifier', '').split(','))

                asg_data.append({
                    'Name': name,
                    'Launch template/configuration': launch_template,
                    'Instances': instances,
                    'Instance Type': instance_types_str,
                    'AMI ID': ami_ids_str,
                    'Security Group ID': security_groups_str,
                    'Load Balancer Target Groups': target_groups_str,
                    'AZ': availability_zones,
                    'Subnet ID': subnet_ids,
                    'Desired Capacity': desired_capacity,
                    'Min': min_size,
                    'Max': max_size
                })
    except Exception as e:
        print(f"Error retrieving Auto Scaling Groups: {e}")
    return asg_data