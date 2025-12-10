from modules.common import exponential_backoff

def list_ebs_volumes(session):
    ebs_data = []
    try:
        ec2_client = session.client('ec2')
        volumes = exponential_backoff(ec2_client.describe_volumes)['Volumes']

        for volume in volumes:
            volume_id = volume.get('VolumeId', 'N/A')
            size_gb = volume.get('Size', 'N/A')
            state = volume.get('State', 'N/A')
            volume_type = volume.get('VolumeType', 'N/A')
            az = volume.get('AvailabilityZone', 'N/A')
            encrypted = 'Enabled' if volume.get('Encrypted', False) else 'Disabled'
            iops = volume.get('Iops', 'N/A')
            throughput = volume.get('Throughput', 'N/A') if 'Throughput' in volume else 'N/A'
            snapshot_id = volume.get('SnapshotId', 'N/A')

            attachments = volume.get('Attachments', [])
            if attachments:
                attachment_info = ', '.join([f"{att.get('InstanceId', 'N/A')} ({att.get('State', 'N/A')})" for att in attachments])
            else:
                attachment_info = 'Not Attached'

            ebs_data.append({
                'Volume ID': volume_id,
                'Size (GiB)': size_gb,
                'State': state,
                'Volume Type': volume_type,
                'Availability Zone': az,
                'Encrypted': encrypted,
                'IOPS': iops,
                'Throughput': throughput,
                'Snapshot ID': snapshot_id,
                'Attachment': attachment_info
            })
    except Exception as e:
        print(f"Error retrieving EBS volumes: {e}")
    return ebs_data
