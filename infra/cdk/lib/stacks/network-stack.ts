import { Stack, StackProps, aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";

interface NetworkStackProps extends StackProps {
  vpcCidr: string;
  publicSubnets: {
    id: string;
    availabilityZone: string;
    cidrBlock: string;
  }[];
}

export class NetworkStack extends Stack {
  constructor(scope: Construct, id: string, props: NetworkStackProps) {
    super(scope, id, props);

    const vpc = new ec2.Vpc(this, "Vpc", {
      ipAddresses: ec2.IpAddresses.cidr(props.vpcCidr),
      natGateways: 0,
      subnetConfiguration: [],
    });

    const internetGateway = new ec2.CfnInternetGateway(this, "InternetGateway");

    new ec2.CfnVPCGatewayAttachment(this, "InternetGatewayAttachment", {
      internetGatewayId: internetGateway.ref,
      vpcId: vpc.vpcId,
    });

    props.publicSubnets.forEach((subnet) => {
      new ec2.CfnSubnet(this, subnet.id, {
        availabilityZone: subnet.availabilityZone,
        cidrBlock: subnet.cidrBlock,
        mapPublicIpOnLaunch: false,
        vpcId: vpc.vpcId,
      });
    });
  }
}
