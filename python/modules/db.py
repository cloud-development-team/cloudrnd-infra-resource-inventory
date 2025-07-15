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
            name_tag = next((tag['Value'] for tag in subnet.get('Tags', []) if tag['Key'] == 'Name'), '-')
            subnet_name_map[subnet_id] = name_tag

        # Subnet Group ID → [SubnetID (Name), ...] 매핑
        subnet_group_map = {}
        subnet_groups = exponential_backoff(rds_client.describe_db_subnet_groups)
        for group in subnet_groups.get('DBSubnetGroups', []):
            group_name = group['DBSubnetGroupName']
            subnet_entries = [
                f"{subnet['SubnetIdentifier']} ({subnet_name_map.get(subnet['SubnetIdentifier'], '-')})"
                for subnet in group.get('Subnets', [])
            ]
            subnet_group_map[group_name] = subnet_entries

        clusters = exponential_backoff(rds_client.describe_db_clusters)['DBClusters']

        for cluster in clusters:
            cluster_name = cluster.get('DBClusterIdentifier', 'N/A')
            port = cluster.get('Port', 'N/A')
            status = cluster.get('Status', 'N/A')
            engine_version = cluster.get('EngineVersion', 'N/A')
            rds_type = cluster.get('Engine', 'N/A')

            subnet_group_id = cluster.get('DBSubnetGroup', 'N/A')
            subnet_str = ', '.join(subnet_group_map.get(subnet_group_id, ['-']))

            security_group = ', '.join(
                [group['VpcSecurityGroupId'] for group in cluster.get('VpcSecurityGroups', [])]
            ) if 'VpcSecurityGroups' in cluster else 'N/A'

            automated_backups = 'Enabled' if cluster.get('BackupRetentionPeriod', 0) > 0 else 'Disabled'
            encryption_at_rest = 'Enabled' if cluster.get('StorageEncrypted', False) else 'Disabled'
            cloudwatch_logs = ', '.join(cluster.get('EnabledCloudwatchLogsExports', [])) if 'EnabledCloudwatchLogsExports' in cluster else 'Disabled'
            deletion_protection = 'Enabled' if cluster.get('DeletionProtection', False) else 'Disabled'
            tls_enabled = 'Enabled' if cluster.get('IAMDatabaseAuthenticationEnabled', False) else 'Disabled'

            rds_data.append({
                'Cluster Name': cluster_name,
                'Port': port,
                'Status': status,
                'Engine Version': engine_version,
                'RDS Type': rds_type,
                'Subnet Group ID': subnet_group_id,
                'Subnet (ID and Name)': subnet_str,
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
