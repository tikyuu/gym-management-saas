import { Stack, StackProps, Tags, aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";

interface NetworkStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
  vpcCidr: string;
  publicSubnets: {
    id: string;
    name: string;
    availabilityZone: string;
    cidrBlock: string;
  }[];
}

export class NetworkStack extends Stack {
  constructor(scope: Construct, id: string, props: NetworkStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "network");

    const vpc = new ec2.Vpc(this, "Vpc", {
      ipAddresses: ec2.IpAddresses.cidr(props.vpcCidr),
      natGateways: 0,
      subnetConfiguration: [],
      vpcName: `${resourceNamePrefix}-vpc`,
    });

    const internetGateway = new ec2.CfnInternetGateway(
      this,
      "InternetGateway",
      {
        tags: [
          {
            key: "Name",
            value: `${resourceNamePrefix}-igw`,
          },
        ],
      },
    );

    const internetGatewayAttachment = new ec2.CfnVPCGatewayAttachment(
      this,
      "InternetGatewayAttachment",
      {
        internetGatewayId: internetGateway.ref,
        vpcId: vpc.vpcId,
      },
    );

    const publicRouteTable = new ec2.CfnRouteTable(this, "PublicRouteTable", {
      tags: [
        {
          key: "Name",
          value: `${resourceNamePrefix}-public-rt`,
        },
      ],
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
        tags: [
          {
            key: "Name",
            value: `${resourceNamePrefix}-${subnet.name}`,
          },
        ],
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
