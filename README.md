# AWS Resource Inventory Extractor

A module that uses awscli to extract AWS resources and export them to a structured inventory file.

<p align="center">
  <img src="https://github.com/user-attachments/assets/08ed8337-916c-4ae7-8c1c-66d26ff85329" alt="AWS Resource Inventory Extractor">
</p>


## Tech Stack
- AWSCLI Latest
- Python (In-house developed code)

## Pre-requirements
- 2 vCPU / 8 RAM
- Docker Version >= v24.0.2
- IAM or SSO Auth: Read-Only Permissions (to security)

## Currently Extractable Items

For additional items, please send a request to jaeho.p@hanwha.com

```
  - VPC, VPC Endpoint, Peering Connection
  - Transit Gateway
  - Subnet
  - Security Groups
  - Network ACLs
  - EC2
  - ELB
  - Target Group
  - Auto Scaling
  - ElastiCache
  - CloudFront
  - S3
  - IAM Group, Role, User
  - RDS, DocumentDB
  - MSK
```

## Usage Detail Guide

### You can run the module using a container.

#### Container Image Build
```bash
docker build -t {{imageName}} .
```
#### Container Run
```bash
docker run --rm -it -v {{Your Host Directory}}:/app/inventory {{imageName}}
```

### [ 1 / 2 ] Authenticate with AWS using awscli: IAM or SSO.

- IAM Login
  - Input the below data to IAM login.
    ```
    AWS Access Key ID : (Your IAM user's Access Key ID here.)
    AWS Secret Access Key : (Your IAM user's Secret Access Key here.)
    Default region name : (Your Project Region)
    Default output format :json 
    ```

- SSO Login
  - Input the below data to SSO login.
    ```
    SSO session name (hanwhavision): (Your SSO Session Name, Default: hanwhavision)
    SSO start URL [https://htaic.awsapps.com/start]: (Your SSO URL, Default: https://htaic.awsapps.com/start)
    SSO region [us-west-2]: (Your SSO Region, Default: us-west-2)
    ```
  - Open the following URL and enter the given code.
    
    ![image](https://github.com/user-attachments/assets/ade9aa67-a885-4117-ad52-375ae7ec55be)
  
  - After SSO login, allow access.
  
    ![image](https://github.com/user-attachments/assets/dd72cd0d-7060-45fb-8ae0-bf3b8f52967e)

  - Select AWS Account Profile Config Setup Method.
 
    ![image](https://github.com/user-attachments/assets/e1ab1526-2eee-460e-9767-ac40c85fc8ac)
    - Auto: Extract SSO Accounts Profile Automatically.
    - Manual: Copy & Paste AWS Profile Context.
      ![image](https://github.com/user-attachments/assets/267737a0-c0db-46d4-8303-5ed6c7f04635)
      ```
      [profile {{Project_1 profile name}}]
      sso_session = {{SSO Session name}}
      sso_account_id = {{Project_1 AWS account}}
      sso_role_name = {{Your role name}}
      region = {{Account region}}
      output = json

      [profile {{Project_2 profile name}}]
      sso_session = {{SSO Session name}}
      sso_account_id = {{Project_2 AWS account}}
      sso_role_name = {{Your role name}}
      region = {{Account region}}
      output = json
      ```
### [ 2 / 2 ] Extract to structured inventory file.
- The inventory file(s) will be successfully created in the inventory volume.
