import { aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";
import type { SubnetConfig } from "../types/subnet-config";

interface PublicNetworkConstructProps {
  vpcId: string;
  resourceNamePrefix: string;
  subnets: SubnetConfig[];
}

export class PublicNetworkConstruct extends Construct {
  public readonly natGateway: ec2.CfnNatGateway;

  constructor(scope: Construct, id: string, props: PublicNetworkConstructProps) {
    super(scope, id);

    const internetGateway = new ec2.CfnInternetGateway(
      this,
      "InternetGateway",
      {
        tags: [
          {
            key: "Name",
            value: `${props.resourceNamePrefix}-igw`,
          },
        ],
      },
    );

    const internetGatewayAttachment = new ec2.CfnVPCGatewayAttachment(
      this,
      "InternetGatewayAttachment",
      {
        internetGatewayId: internetGateway.ref,
        vpcId: props.vpcId,
      },
    );

    const natElasticIp = new ec2.CfnEIP(this, "NatElasticIp", {
      domain: "vpc",
      tags: [
        {
          key: "Name",
          value: `${props.resourceNamePrefix}-nat-eip`,
        },
      ],
    });

    natElasticIp.addResourceDependency(internetGatewayAttachment);

    const publicRouteTable = new ec2.CfnRouteTable(this, "PublicRouteTable", {
      tags: [
        {
          key: "Name",
          value: `${props.resourceNamePrefix}-public-rt`,
        },
      ],
      vpcId: props.vpcId,
    });

    const publicDefaultRoute = new ec2.CfnRoute(this, "PublicDefaultRoute", {
      destinationCidrBlock: "0.0.0.0/0",
      gatewayId: internetGateway.ref,
      routeTableId: publicRouteTable.ref,
    });

    publicDefaultRoute.addResourceDependency(
      internetGatewayAttachment,
    );

    const publicSubnets = props.subnets.map((subnet) => {
      const publicSubnet = new ec2.CfnSubnet(this, subnet.id, {
        availabilityZone: subnet.availabilityZone,
        cidrBlock: subnet.cidrBlock,
        mapPublicIpOnLaunch: false,
        tags: [
          {
            key: "Name",
            value: `${props.resourceNamePrefix}-${subnet.name}`,
          },
        ],
        vpcId: props.vpcId,
      });

      new ec2.CfnSubnetRouteTableAssociation(
        this,
        `${subnet.id}RouteTableAssociation`,
        {
          routeTableId: publicRouteTable.ref,
          subnetId: publicSubnet.ref,
        },
      );

      return publicSubnet;
    });

    this.natGateway = new ec2.CfnNatGateway(this, "NatGateway", {
      allocationId: natElasticIp.attrAllocationId,
      subnetId: publicSubnets[0].ref,
      tags: [
        {
          key: "Name",
          value: `${props.resourceNamePrefix}-nat-gateway`,
        },
      ],
    });

    this.natGateway.addResourceDependency(
      internetGatewayAttachment,
    );
  }
}
