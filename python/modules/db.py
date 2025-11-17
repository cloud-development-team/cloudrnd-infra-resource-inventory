from collections import defaultdict
from modules.common import exponential_backoff

def list_db_clusters(session):
    rds_data = []
    try:
        rds_client = session.client('rds')
        ec2_client = session.client('ec2')

        # Subnet ID → Name 매핑
        subnet_name_map = {}
        subnets = exponential_backoff(ec2_client.describe_subnets)
        for subnet in subnets['Subnets']:
            subnet_id = subnet['SubnetId']
            name_tag = next(
                (tag['Value'] for tag in subnet.get('Tags', []) if tag['Key'] == 'Name'),
                '-'
            )
            subnet_name_map[subnet_id] = name_tag

        # Subnet Group ID → [Subnet ID], [Subnet Name] 매핑
        subnet_group_id_to_ids = {}
        subnet_group_id_to_names = {}
        subnet_groups = exponential_backoff(rds_client.describe_db_subnet_groups)
        for group in subnet_groups.get('DBSubnetGroups', []):
            group_name = group['DBSubnetGroupName']
            subnet_ids = [subnet['SubnetIdentifier'] for subnet in group.get('Subnets', [])]
            subnet_names = [subnet_name_map.get(sid, '-') for sid in subnet_ids]
            subnet_group_id_to_ids[group_name] = subnet_ids
            subnet_group_id_to_names[group_name] = subnet_names

        # 클러스터별 DB Type 집계 (인스턴스 타입)
        cluster_to_db_types = defaultdict(set)     # cluster_id -> {db.r6g.large, ...}

        instances = exponential_backoff(rds_client.describe_db_instances)
        for inst in instances.get('DBInstances', []):
            cluster_id = inst.get('DBClusterIdentifier')  # 단일 인스턴스(RDS)면 None
            if not cluster_id:
                continue  # 여기서는 Cluster 인벤토리만 보므로 단일 인스턴스는 스킵

            db_class = inst.get('DBInstanceClass', '-')
            cluster_to_db_types[cluster_id].add(db_class)

        # 클러스터 조회
        clusters = exponential_backoff(rds_client.describe_db_clusters)['DBClusters']

        for cluster in clusters:
            cluster_name = cluster.get('DBClusterIdentifier', 'N/A')
            port = cluster.get('Port', 'N/A')
            status = cluster.get('Status', 'N/A')
            engine_version = cluster.get('EngineVersion', 'N/A')
            rds_type = cluster.get('Engine', 'N/A')

            subnet_group_id = cluster.get('DBSubnetGroup', 'N/A')
            subnet_ids = subnet_group_id_to_ids.get(subnet_group_id, ['-'])
            subnet_names = subnet_group_id_to_names.get(subnet_group_id, ['-'])

            security_group = ', '.join(
                [group['VpcSecurityGroupId'] for group in cluster.get('VpcSecurityGroups', [])]
            ) if 'VpcSecurityGroups' in cluster else 'N/A'

            automated_backups = 'Enabled' if cluster.get('BackupRetentionPeriod', 0) > 0 else 'Disabled'
            encryption_at_rest = 'Enabled' if cluster.get('StorageEncrypted', False) else 'Disabled'
            cloudwatch_logs = ', '.join(cluster.get('EnabledCloudwatchLogsExports', [])) \
                if 'EnabledCloudwatchLogsExports' in cluster else 'Disabled'
            deletion_protection = 'Enabled' if cluster.get('DeletionProtection', False) else 'Disabled'
            tls_enabled = 'Enabled' if cluster.get('IAMDatabaseAuthenticationEnabled', False) else 'Disabled'

            # DB Type 정보 (클러스터 내 인스턴스 타입 집합)
            db_types = ', '.join(sorted(cluster_to_db_types.get(cluster_name, {'-'})))

            # Writer / Reader 개수 계산 (DBClusterMembers 기반)
            members = cluster.get('DBClusterMembers', [])
            writer_count = sum(1 for m in members if m.get('IsClusterWriter'))
            reader_count = len(members) - writer_count

            rds_data.append({
                'Cluster Name': cluster_name,
                'Port': port,
                'Status': status,
                'Engine Version': engine_version,
                'RDS Type': rds_type,
                'DB Type': db_types,                     # ex) db.r6g.large, db.r6g.xlarge
                'Writer Count': writer_count,            # ex) 1
                'Reader Count': reader_count,            # ex) 2
                'Subnet Group ID': subnet_group_id,
                'Subnet ID': ', '.join(subnet_ids),
                'Subnet Name': ', '.join(subnet_names),
                'Security Group': security_group,
                'Automated Backups': automated_backups,
                'Encryption At Rest': encryption_at_rest,
                'CloudWatch Logs': cloudwatch_logs,
                'Deletion Protection': deletion_protection,
                'TLS Enabled': tls_enabled
            })

    except Exception as e:
        print(f"Error retrieving RDS clusters: {e}")

    return rds_data
