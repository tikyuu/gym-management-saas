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

    const internetGatewayAttachment = new ec2.CfnVPCGatewayAttachment(
      this,
      "InternetGatewayAttachment",
      {
        internetGatewayId: internetGateway.ref,
        vpcId: vpc.vpcId,
      },
    );

    const publicRouteTable = new ec2.CfnRouteTable(this, "PublicRouteTable", {
      vpcId: vpc.vpcId,
    });

    const publicDefaultRoute = new ec2.CfnRoute(this, "PublicDefaultRoute", {
      destinationCidrBlock: "0.0.0.0/0",
      gatewayId: internetGateway.ref,
      routeTableId: publicRouteTable.ref,
    });

    publicDefaultRoute.addResourceDependency(internetGatewayAttachment);

    props.publicSubnets.forEach((subnet) => {
      const publicSubnet = new ec2.CfnSubnet(this, subnet.id, {
        availabilityZone: subnet.availabilityZone,
        cidrBlock: subnet.cidrBlock,
        mapPublicIpOnLaunch: false,
        vpcId: vpc.vpcId,
      });

      new ec2.CfnSubnetRouteTableAssociation(
        this,
        `${subnet.id}RouteTableAssociation`,
        {
          routeTableId: publicRouteTable.ref,
          subnetId: publicSubnet.ref,
        },
      );
    });
  }
}
