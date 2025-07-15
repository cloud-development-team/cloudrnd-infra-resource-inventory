from modules.common import exponential_backoff

def list_eks_clusters(session):
    eks_client = session.client('eks')
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

    cluster_names = exponential_backoff(eks_client.list_clusters).get("clusters", [])
    result = []

    for cluster_name in cluster_names:
        cluster_info = exponential_backoff(
            eks_client.describe_cluster, name=cluster_name
        ).get("cluster", {})

        created_at = cluster_info.get("createdAt")
        created_at_str = (
            created_at.astimezone().replace(tzinfo=None).isoformat()
            if created_at else "-"
        )

        subnet_ids = cluster_info.get("resourcesVpcConfig", {}).get("subnetIds", [])
        subnet_names = [subnet_name_map.get(sid, '-') for sid in subnet_ids]

        result.append({
            "Cluster Name": cluster_name,
            "Status": cluster_info.get("status", "-"),
            "Version": cluster_info.get("version", "-"),
            "Endpoint": cluster_info.get("endpoint", "-"),
            "Role ARN": cluster_info.get("roleArn", "-"),
            "VPC ID": cluster_info.get("resourcesVpcConfig", {}).get("vpcId", "-"),
            "Subnet ID": ', '.join(subnet_ids),
            "Subnet Name": ', '.join(subnet_names),
            "Security Group IDs": ", ".join(
                cluster_info.get("resourcesVpcConfig", {}).get("securityGroupIds", [])
            ),
            "Created At": created_at_str,
            "ARN": cluster_info.get("arn", "-")
        })

    return result
