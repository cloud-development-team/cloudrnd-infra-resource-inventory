from modules.common import exponential_backoff

def list_auto_scaling_groups(session):
    asg_data = []
    try:
        asg_client = session.client('autoscaling')
        ec2_client = session.client('ec2')
        elb_client = session.client('elbv2')

        # Subnet ID → Name 매핑
        subnet_name_map = {}
        subnets = exponential_backoff(ec2_client.describe_subnets)
        for subnet in subnets['Subnets']:
            subnet_id = subnet['SubnetId']
            name_tag = next((tag['Value'] for tag in subnet.get('Tags', []) if tag['Key'] == 'Name'), '-')
            subnet_name_map[subnet_id] = name_tag

        paginator = asg_client.get_paginator('describe_auto_scaling_groups')
        response_iterator = paginator.paginate()

        for response in response_iterator:
            for asg in response['AutoScalingGroups']:
                name = asg['AutoScalingGroupName']

                # Launch Template or Launch Configuration
                if 'LaunchTemplate' in asg:
                    lt = asg['LaunchTemplate']
                    launch_template = f"{lt['LaunchTemplateName']} (Version: {lt['Version']})"
                else:
                    launch_template = asg.get('LaunchConfigurationName', '-')

                # Instance Info
                instances_details, instance_types, ami_ids = [], [], []
                security_groups_set = set()

                for instance in asg['Instances']:
                    instance_id = instance['InstanceId']
                    try:
                        instance_info = exponential_backoff(ec2_client.describe_instances, InstanceIds=[instance_id])
                        inst = instance_info['Reservations'][0]['Instances'][0]
                        instance_types.append(inst['InstanceType'])
                        ami_ids.append(inst['ImageId'])
                        sg_ids = [sg['GroupId'] for sg in inst.get('SecurityGroups', [])]
                        security_groups_set.update(sg_ids)
                        instances_details.append(instance_id)
                    except Exception as e:
                        print(f"Error retrieving instance info for {instance_id}: {e}")

                instances_str = ', '.join(instances_details)
                instance_types_str = ', '.join(instance_types)
                ami_ids_str = ', '.join(ami_ids)
                security_groups_str = ', '.join(security_groups_set)
                desired_capacity = asg['DesiredCapacity']
                min_size = asg['MinSize']
                max_size = asg['MaxSize']
                availability_zones = ', '.join(asg['AvailabilityZones'])

                # Target Groups
                target_groups = []
                for tg_arn in asg.get('TargetGroupARNs', []):
                    try:
                        tg_info = exponential_backoff(elb_client.describe_target_groups, TargetGroupArns=[tg_arn])
                        tg_name = tg_info['TargetGroups'][0]['TargetGroupName']
                        target_groups.append(tg_name)
                    except Exception as e:
                        print(f"Error retrieving target group info for {tg_arn}: {e}")
                target_groups_str = ', '.join(target_groups)

                # Subnet IDs + Names
                raw_subnet_ids = asg.get('VPCZoneIdentifier', '').split(',')
                subnet_strs = [f"{sid} ({subnet_name_map.get(sid, '-')})" for sid in raw_subnet_ids if sid]
                subnet_info_str = ', '.join(subnet_strs)

                asg_data.append({
                    'Name': name,
                    'Launch template/configuration': launch_template,
                    'Instances': instances_str,
                    'Instance Type': instance_types_str,
                    'AMI ID': ami_ids_str,
                    'Security Group ID': security_groups_str,
                    'Load Balancer Target Groups': target_groups_str,
                    'AZ': availability_zones,
                    'Subnet (ID and Name)': subnet_info_str,
                    'Desired Capacity': desired_capacity,
                    'Min': min_size,
                    'Max': max_size
                })

    except Exception as e:
        print(f"Error retrieving Auto Scaling Groups: {e}")
    return asg_data
