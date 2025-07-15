from modules.common import exponential_backoff

def list_opensearch_clusters(session):
    os_client = session.client('opensearch')
    ec2_client = session.client('ec2')

    # 미리 전체 Subnet ID → Name 매핑 수집
    subnet_name_map = {}
    subnets = exponential_backoff(ec2_client.describe_subnets)
    for subnet in subnets['Subnets']:
        subnet_id = subnet['SubnetId']
        name_tag = next((tag['Value'] for tag in subnet.get('Tags', []) if tag['Key'] == 'Name'), '-')
        subnet_name_map[subnet_id] = name_tag

    domains = exponential_backoff(os_client.list_domain_names).get("DomainNames", [])
    result = []

    for domain in domains:
        domain_name = domain.get("DomainName", "-")
        domain_info = exponential_backoff(
            os_client.describe_domain,
            DomainName=domain_name
        ).get("DomainStatus", {})

        # Subnet ID + Name 표시
        subnet_ids = domain_info.get("VPCOptions", {}).get("SubnetIds", [])
        subnet_strs = [f"{sid} ({subnet_name_map.get(sid, '-')})" for sid in subnet_ids]
        subnet_summary = ', '.join(subnet_strs)

        result.append({
            "Domain Name": domain_name,
            "Engine Version": domain_info.get("EngineVersion", "-"),
            "Endpoint": domain_info.get("Endpoint", "-"),
            "VPC ID": domain_info.get("VPCOptions", {}).get("VPCId", "-"),
            "Subnet (ID and Name)": subnet_summary,
            "Instance Type": domain_info.get("ClusterConfig", {}).get("InstanceType", "-"),
            "Instance Count": domain_info.get("ClusterConfig", {}).get("InstanceCount", "-"),
            "Dedicated Master": domain_info.get("ClusterConfig", {}).get("DedicatedMasterEnabled", False),
            "Zone Awareness": domain_info.get("ClusterConfig", {}).get("ZoneAwarenessEnabled", False),
            "Created": domain_info.get("Created", False),
            "Deleted": domain_info.get("Deleted", False),
            "ARN": domain_info.get("ARN", "-")
        })

    return result
