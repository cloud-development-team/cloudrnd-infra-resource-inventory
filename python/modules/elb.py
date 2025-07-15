from modules.common import exponential_backoff

def list_elbs(session):
    elb_data = []
    try:
        elb_client = session.client('elbv2')
        ec2_client = session.client('ec2')

        # 전체 Subnet ID → Name 매핑 미리 수집
        subnet_name_map = {}
        subnets = exponential_backoff(ec2_client.describe_subnets)
        for subnet in subnets['Subnets']:
            subnet_id = subnet['SubnetId']
            name_tag = next((tag['Value'] for tag in subnet.get('Tags', []) if tag['Key'] == 'Name'), '-')
            subnet_name_map[subnet_id] = name_tag

        # ELB 목록 가져오기
        paginator = elb_client.get_paginator('describe_load_balancers')
        response_iterator = paginator.paginate()

        for response in response_iterator:
            for elb in response['LoadBalancers']:
                name = elb['LoadBalancerName']
                dns_name = elb['DNSName']
                state_code = elb['State']['Code']
                scheme = elb['Scheme']
                lb_type = elb['Type']
                availability_zones = ', '.join([az['ZoneName'] for az in elb['AvailabilityZones']])

                # Subnet ID + Name 표시
                subnet_entries = []
                for az in elb['AvailabilityZones']:
                    subnet_id = az['SubnetId']
                    subnet_name = subnet_name_map.get(subnet_id, '-')
                    subnet_entries.append(f"{subnet_id} ({subnet_name})")
                subnet_str = ', '.join(subnet_entries)

                # ELB Security Groups
                security_groups = elb.get('SecurityGroups', [])
                security_groups_str = ', '.join(security_groups)

                # Cross-Zone Load Balancing, Stickiness, Access Logs and Tags
                cross_zone, stickiness, access_logs = '-', '-', '-'

                try:
                    attributes = exponential_backoff(
                        elb_client.describe_load_balancer_attributes,
                        LoadBalancerArn=elb['LoadBalancerArn']
                    )
                    for attr in attributes['Attributes']:
                        if attr['Key'] == 'load_balancing.cross_zone.enabled':
                            cross_zone = attr['Value']
                        elif attr['Key'] == 'access_logs.s3.enabled':
                            access_logs = attr['Value']
                except Exception as e:
                    print(f"Error retrieving attributes for ELB {name}: {e}")

                # ELB Tags
                try:
                    tags_response = exponential_backoff(
                        elb_client.describe_tags,
                        ResourceArns=[elb['LoadBalancerArn']]
                    )
                    tags = {tag['Key']: tag['Value'] for tag in tags_response['TagDescriptions'][0]['Tags']}
                    tags_str = ', '.join([f"{k}: {v}" for k, v in tags.items()])
                except Exception as e:
                    print(f"Error retrieving tags for ELB {name}: {e}")
                    tags_str = '-'

                elb_data.append({
                    'Name': name,
                    'DNS Name': dns_name,
                    'State Code': state_code,
                    'Scheme': scheme,
                    'Type': lb_type,
                    'AZ': availability_zones,
                    'Subnet (ID and Name)': subnet_str,
                    'ELB Security Group ID': security_groups_str,
                    'Cross-Zone Load Balancing': cross_zone,
                    'Stickiness': stickiness,
                    'Access Logs': access_logs,
                    'Tag': tags_str
                })
    except Exception as e:
        print(f"Error retrieving ELBs: {e}")
    return elb_data
