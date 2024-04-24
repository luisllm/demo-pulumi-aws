"""An AWS Python Pulumi program"""

import pulumi
import pulumi_aws as aws


# This function logs a message that can be seen in a `pulumi up` or `pulumi preview`.
def log_message(message: str):
    # Logging an info level message. This will appear in both preview and update if the log level is set to at least 'info'.
    pulumi.log.info(message)
# Call the log_message function with a message to log
#log_message("This message will be logged during preview and update.")


ami = aws.ec2.get_ami(
  most_recent=True,
  owners=["amazon"],
  filters=[aws.ec2.GetAmiFilterArgs(name="name", values=["amzn2-ami-hvm-*"])],
)


# Pulumi config variables so that they are not hardcoded in the code
# https://www.pulumi.com/docs/concepts/config/
config = pulumi.Config()
ec2_size = config.get("ec2_size") or "t2.micro"



# Replace this with your VPC ID
vpc_id = "vpc-0dfc314f4296b721d"
# Replace this with your public subnets prefix
public_subnet_name_prefix= "test-subnet-public"


# Create a Security Group
sec_group = aws.ec2.SecurityGroup(
  "web-secgroup", 
  description='Enable HTTP access',
  vpc_id=vpc_id,
  ingress=[
    { 'protocol': 'icmp', 'from_port': 8, 'to_port': 0, 'cidr_blocks': ['0.0.0.0/0'] },
    { 'protocol': 'tcp', 'from_port': 80, 'to_port': 80, 'cidr_blocks': ['0.0.0.0/0'] }
  ],
  egress=[
    { 'protocol': 'tcp', 'from_port': 80, 'to_port': 80, 'cidr_blocks': ['0.0.0.0/0'] }
  ]
)

# Get public subnet ids to use them when creating the LB
public_subnets = aws.ec2.get_subnets(
  filters=[aws.ec2.GetSubnetsFilterArgs(
    name="tag:Name",
    values=[public_subnet_name_prefix+'*']
  )]
)

# Create a LB
lb = aws.lb.LoadBalancer(
  "public-loadbalancer",
  internal="false",
  security_groups=[sec_group.id],
  subnets=public_subnets.ids,
  load_balancer_type="application",
)

target_group = aws.lb.TargetGroup(
  "target-group",
  port=80,
  protocol="HTTP",
  target_type="ip",
  vpc_id=vpc_id
)

listener = aws.lb.Listener(
  "listener",
  load_balancer_arn=lb.arn,
  port=80,
  default_actions=[{
    "type": "forward",
    "target_group_arn": target_group.arn
  }]
)

# Create one EC2 per AZ, and stores the IPs and hostanmes
ec2s_ips = []
ec2s_hostnames = []
# This is only needed because the ssubnet names contain '1', '2', etc
i = 1

for az in aws.get_availability_zones().names:
  
  # Create EC2 only in the first 2 AZs
  if az == 'us-east-1a' or az == 'us-east-1b':

    # Get the subnet_id based on the subnet_name
    public_subnet_name = f'{public_subnet_name_prefix}{i}-{az}'
    #log_message(public_subnet_name)
    public_subnet = aws.ec2.get_subnet(
      filters=[aws.ec2.GetSubnetFilterArgs(
        name="tag:Name",
        values=[public_subnet_name]
      )]
    )
    #log_message(public_subnet)

    ec2_instance = aws.ec2.Instance(
      f'web-server-{az}',
      instance_type=ec2_size,
      vpc_security_group_ids=[sec_group.id],
      ami=ami.id,
      user_data="""#!/bin/bash
echo \"Hello, World -- from {}!\" > index.html
nohup python -m SimpleHTTPServer 80 &
""".format(az),
      availability_zone=az,
      subnet_id=public_subnet.id,
      tags={
        "Name": "web-server",
      },
    )

    # Attach the EC2 to the LB target group
    attachment = aws.lb.TargetGroupAttachment(
      f'web-server-{az}',
      target_group_arn=target_group.arn,
      target_id=ec2_instance.private_ip,
      port=80,
    )

    # Store the IP and Hostname of the EC2
    ec2s_ips.append(ec2_instance.public_ip)
    ec2s_hostnames.append(ec2_instance.public_dns)
    
    #ec2_instance.public_ip.apply(lambda public_ip: log_message(public_ip))

  i += 1


pulumi.export('EC2s IPs', ec2s_ips)
pulumi.export('EC2s Hostnames', ec2s_hostnames)
pulumi.export('url', lb.dns_name)
