from modules.common import exponential_backoff

def list_ec2_instances(session):
    ec2_data = []

    try:
        region = session.region_name or session.client('ec2').meta.region_name
        sts_client = session.client('sts')
        account_id = sts_client.get_caller_identity().get('Account', '-')
        profile_name = session.profile_name if hasattr(session, 'profile_name') else '-'

        ec2_client = session.client('ec2')
        ssm_client = session.client('ssm')

        # Subnet ID → Name 매핑
        subnet_name_map = {}
        subnets = exponential_backoff(ec2_client.describe_subnets)
        for subnet in subnets['Subnets']:
            subnet_id = subnet['SubnetId']
            name_tag = next((tag['Value'] for tag in subnet.get('Tags', []) if tag['Key'] == 'Name'), '-')
            subnet_name_map[subnet_id] = name_tag

        instances = ec2_client.describe_instances()

        for reservation in instances.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                # SSM 관리 여부 확인
                def ssm_check():
                    return ssm_client.describe_instance_information(Filters=[
                        {'Key': 'InstanceIds', 'Values': [instance['InstanceId']]}
                    ])
                try:
                    ssm_response = exponential_backoff(ssm_check)
                    ssm_managed = len(ssm_response.get('InstanceInformationList', [])) > 0
                except Exception as e:
                    print(f"Error checking SSM for {instance['InstanceId']}: {e}")
                    ssm_managed = False

                # EBS 볼륨 정보
                volumes_info = []
                for device in instance.get('BlockDeviceMappings', []):
                    if 'Ebs' in device:
                        def volume_info():
                            return ec2_client.describe_volumes(VolumeIds=[device['Ebs']['VolumeId']])
                        try:
                            volume = exponential_backoff(volume_info)
                            volumes_info.append({
                                "VolumeId": device['Ebs']['VolumeId'],
                                "Size (GB)": volume['Volumes'][0]['Size']
                            })
                        except Exception as e:
                            print(f"Error retrieving volume info for {device['Ebs']['VolumeId']}: {e}")

                volumes = ', '.join([vol['VolumeId'] for vol in volumes_info])
                volume_sizes = ', '.join([f"{vol['Size (GB)']} GB" for vol in volumes_info])

                # 태그 파싱
                tags = instance.get('Tags', [])
                tags_parsed = ', '.join([f"{tag['Key']}: {tag['Value']}" for tag in tags])
                instance_name = next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), '-')

                # 서브넷 이름
                subnet_id = instance.get('SubnetId', '-')
                subnet_name = subnet_name_map.get(subnet_id, '-')

                # 보안 그룹, 키페어, IAM 역할
                security_groups = instance.get('SecurityGroups', [])
                security_groups_parsed = ', '.join([g['GroupName'] for g in security_groups])
                key_name = instance.get('KeyName', '-')
                iam_instance_profile = instance.get('IamInstanceProfile', {})
                iam_role_name = '-'
                if 'Arn' in iam_instance_profile:
                    iam_role_name = iam_instance_profile['Arn'].split('/')[-1]

                # AMI ID 및 AMI Name 조회
                image_id = instance.get('ImageId', '-')
                try:
                    def ami_info():
                        return ec2_client.describe_images(ImageIds=[image_id])
                    images = exponential_backoff(ami_info).get('Images', [])
                    ami_name = images[0].get('Name', '-') if images else '-'
                except Exception as e:
                    print(f"Error retrieving AMI info for {image_id}: {e}")
                    ami_name = '-'

                ec2_data.append({
                    'Account ID': account_id,
                    'Profile Name': profile_name,
                    'Region': region,
                    'Instance Name': instance_name,
                    'Instance ID': instance['InstanceId'],
                    'Instance Type': instance['InstanceType'],
                    'State': instance['State']['Name'],
                    'SSM Managed': 'Yes' if ssm_managed else 'No',
                    'VPC ID': instance.get('VpcId', '-'),
                    'Subnet ID': subnet_id,
                    'Subnet Name': subnet_name,
                    'Availability Zone': instance['Placement']['AvailabilityZone'],
                    'Key Name': key_name,
                    'IAM Role': iam_role_name,
                    'Private IP Address': instance.get('PrivateIpAddress', '-'),
                    'Public IP Address': instance.get('PublicIpAddress', '-'),
                    'Launch Time': instance['LaunchTime'].strftime("%Y-%m-%d %H:%M:%S"),
                    'AMI ID': image_id,
                    'AMI Name': ami_name,
                    'Volumes': volumes,
                    'Volume Sizes': volume_sizes,
                    'Security Groups': security_groups_parsed,
                    'Tags': tags_parsed
                })

    except Exception as e:
        print(f"Error retrieving EC2 instances: {e}")

    return ec2_data
