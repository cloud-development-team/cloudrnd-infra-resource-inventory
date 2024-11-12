from modules.common import exponential_backoff

def list_nacls(session):
    ec2_client = session.client('ec2')
    nacls = []

    try:
        # Retrieve all NACLs
        response = exponential_backoff(ec2_client.describe_network_acls)
        
        for nacl in response.get('NetworkAcls', []):
            nacl_id = nacl.get('NetworkAclId', '-')
            vpc_id = nacl.get('VpcId', '-')
            region = session.region_name
            name = '-'
            for tag in nacl.get('Tags', []):
                if tag.get('Key') == 'Name':
                    name = tag.get('Value', '-')
                    break
            
            # Extract entries (rules) from the NACL
            for entry in nacl.get('Entries', []):
                rule_number = entry.get('RuleNumber', '-')
                if rule_number == 32767:
                    rule_number = '*'
                rule_type = 'Inbound' if not entry.get('Egress') else 'Outbound'
                protocol = entry.get('Protocol', '-')
                protocol_mapping = {'-1': 'All', '6': 'TCP', '17': 'UDP', '1': 'ICMP'}
                protocol = protocol_mapping.get(protocol, protocol)
                port_range = '-'
                if 'PortRange' in entry:
                    port_range = f"{entry['PortRange'].get('From', '-')}-{entry['PortRange'].get('To', '-')}"
                source = entry.get('CidrBlock', '-')
                allow_deny = 'Allow' if entry.get('RuleAction') == 'allow' else 'Deny'

                nacls.append({
                    'Name': name,
                    'ID': nacl_id,
                    'Region': region,
                    'VPC': vpc_id,
                    'Direction': rule_type,
                    'Rule': rule_number,
                    'Type': 'Custom traffic' if protocol != 'All' else 'All traffic',
                    'Protocol': protocol,
                    'Port Range': port_range,
                    'Source': source,
                    'Allow / Deny': allow_deny
                })
    
    except (BotoCoreError) as e:
        print(f"Error retrieving NACLs: {e}")

    return nacls
