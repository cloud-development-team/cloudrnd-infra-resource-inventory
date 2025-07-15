from modules.common import exponential_backoff

def list_kafka_clusters(session):
    kafka_data = []

    try:
        kafka_client = session.client('kafka')
        ec2_client = session.client('ec2')

        # 서브넷 ID → Name 매핑 미리 생성
        subnet_name_map = {}
        subnets = exponential_backoff(ec2_client.describe_subnets)
        for subnet in subnets['Subnets']:
            subnet_id = subnet['SubnetId']
            name_tag = next((tag['Value'] for tag in subnet.get('Tags', []) if tag['Key'] == 'Name'), '-')
            subnet_name_map[subnet_id] = name_tag

        paginator = kafka_client.get_paginator('list_clusters')
        response_iterator = paginator.paginate()

        for response in response_iterator:
            for cluster in response['ClusterInfoList']:
                cluster_name = cluster['ClusterName']
                kafka_version = cluster.get('CurrentBrokerSoftwareInfo', {}).get('KafkaVersion', '-')
                cluster_status = cluster.get('State', '-')

                subnet_ids = []
                subnet_strs = []
                security_groups = []
                broker_instance_type = '-'
                brokers_per_az = 0
                total_brokers = 0
                ebs_volume_size = '-'
                kms_key_arn = '-'

                try:
                    cluster_info = exponential_backoff(
                        kafka_client.describe_cluster,
                        ClusterArn=cluster['ClusterArn']
                    )

                    if 'ClusterInfo' in cluster_info:
                        info = cluster_info['ClusterInfo']
                        broker_node_group_info = info.get('BrokerNodeGroupInfo', {})

                        subnet_ids = broker_node_group_info.get('ClientSubnets', [])
                        subnet_strs = [f"{sid} ({subnet_name_map.get(sid, '-')})" for sid in subnet_ids]

                        security_groups = broker_node_group_info.get('SecurityGroups', [])
                        broker_instance_type = broker_node_group_info.get('InstanceType', '-')
                        total_brokers = info.get('NumberOfBrokerNodes', 0)
                        brokers_per_az = total_brokers // len(subnet_ids) if subnet_ids else 0

                        storage_info = broker_node_group_info.get('StorageInfo', {}).get('EbsStorageInfo', {})
                        ebs_volume_size = storage_info.get('VolumeSize', '-')

                        kms_key_arn = info.get('EncryptionInfo', {}).get('EncryptionAtRest', {}).get('DataVolumeKMSKeyId', '-')

                except Exception as e:
                    print(f"Error retrieving cluster info for {cluster_name}: {e}")

                kafka_data.append({
                    'Cluster Name': cluster_name,
                    'Kafka Version': kafka_version,
                    'Status': cluster_status,
                    'Subnet (ID and Name)': ', '.join(subnet_strs) if subnet_strs else '-',
                    'Security Group IDs': ', '.join(security_groups) if security_groups else '-',
                    'Broker Instance Type': broker_instance_type,
                    'Brokers per AZ': brokers_per_az,
                    'Total Brokers': total_brokers,
                    'EBS Volume Size (GiB)': ebs_volume_size,
                    'KMS Key ARN': kms_key_arn,
                })

    except Exception as e:
        print(f"Error retrieving Kafka Clusters: {e}")

    return kafka_data
