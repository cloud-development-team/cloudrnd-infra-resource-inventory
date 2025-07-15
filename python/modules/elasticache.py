from modules.common import exponential_backoff

def list_elasticache_clusters(session):
    elasticache_data = []
    try:
        elasticache_client = session.client('elasticache')
        ec2_client = session.client('ec2')

        # Subnet ID → Name 매핑
        subnet_name_map = {}
        subnets = exponential_backoff(ec2_client.describe_subnets)
        for subnet in subnets['Subnets']:
            subnet_id = subnet['SubnetId']
            name_tag = next((tag['Value'] for tag in subnet.get('Tags', []) if tag['Key'] == 'Name'), '-')
            subnet_name_map[subnet_id] = name_tag

        # Subnet Group → [SubnetId, SubnetName] 매핑
        subnet_group_map = {}
        subnet_groups_resp = exponential_backoff(elasticache_client.describe_cache_subnet_groups)
        for group in subnet_groups_resp.get('CacheSubnetGroups', []):
            group_name = group['CacheSubnetGroupName']
            subnet_entries = [
                f"{sn['SubnetIdentifier']} ({subnet_name_map.get(sn['SubnetIdentifier'], '-')})"
                for sn in group.get('Subnets', [])
            ]
            subnet_group_map[group_name] = subnet_entries

        # 클러스터 조회
        paginator = elasticache_client.get_paginator('describe_cache_clusters')
        response_iterator = paginator.paginate(ShowCacheNodeInfo=True)

        for response in response_iterator:
            clusters = response.get('CacheClusters', [])

            for cluster in clusters:
                cluster_name = cluster.get('CacheClusterId', '-')
                region = session.region_name
                engine = cluster.get('Engine', '-')
                subnet_group = cluster.get('CacheSubnetGroupName', '-')
                subnet_info = subnet_group_map.get(subnet_group, ['-'])
                subnet_info_str = ', '.join(subnet_info)

                parameter_group = cluster.get('CacheParameterGroup', {}).get('CacheParameterGroupName', '-')
                security_groups = ', '.join([sg.get('SecurityGroupId', '-') for sg in cluster.get('SecurityGroups', [])])
                cluster_mode = cluster.get('CacheClusterStatus', '-')
                multi_az = cluster.get('PreferredAvailabilityZone', '-') if engine == 'redis' else '-'
                shard = cluster.get('NumCacheNodes', '-')
                node = len(cluster.get('CacheNodes', []))
                backup = 'Enabled' if cluster.get('SnapshotRetentionLimit', 0) > 0 else 'Disabled'
                encryption_at_rest = cluster.get('AtRestEncryptionEnabled', '-') if engine == 'redis' else '-'
                auto_failover = cluster.get('AutoMinorVersionUpgrade', '-') if engine == 'redis' else '-'

                # 태그 조회
                arn = cluster.get('ARN', None)
                if arn:
                    try:
                        tags_response = exponential_backoff(
                            elasticache_client.list_tags_for_resource,
                            ResourceName=arn
                        )
                        tags = ', '.join([f"{tag['Key']}={tag['Value']}" for tag in tags_response.get('TagList', [])])
                    except Exception:
                        tags = '-'
                else:
                    tags = '-'

                elasticache_data.append({
                    'Cluster Name': cluster_name,
                    'Region': region,
                    'Engine': engine,
                    'Subnet Group': subnet_group,
                    'Subnet (ID and Name)': subnet_info_str,
                    'Security Group ID': security_groups,
                    'Parameter Group': parameter_group,
                    'Cluster Mode': cluster_mode,
                    'Multi-AZ': multi_az,
                    'Shard': shard,
                    'Node': node,
                    'Automatic Backups': backup,
                    'Encryption at rest': encryption_at_rest,
                    'Auto-failover': auto_failover,
                    'Tags': tags
                })

    except Exception as e:
        print(f"Error retrieving ElastiCache clusters: {e}")

    return elasticache_data
