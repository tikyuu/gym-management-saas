import { aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";
import type { SubnetConfig } from "../types/subnet-config";

interface PublicNetworkConstructProps {
  vpcId: string;
  resourceNamePrefix: string;
  subnets: SubnetConfig[];
}

export class PublicNetworkConstruct extends Construct {
  public readonly internetGateway: ec2.CfnInternetGateway;
  public readonly internetGatewayAttachment: ec2.CfnVPCGatewayAttachment;
  public readonly natElasticIp: ec2.CfnEIP;
  public readonly natGateway: ec2.CfnNatGateway;
  public readonly publicRouteTable: ec2.CfnRouteTable;
  public readonly subnets: ec2.CfnSubnet[];

  constructor(scope: Construct, id: string, props: PublicNetworkConstructProps) {
    super(scope, id);

    this.internetGateway = new ec2.CfnInternetGateway(
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

    this.internetGatewayAttachment = new ec2.CfnVPCGatewayAttachment(
      this,
      "InternetGatewayAttachment",
      {
        internetGatewayId: this.internetGateway.ref,
        vpcId: props.vpcId,
      },
    );

    this.natElasticIp = new ec2.CfnEIP(this, "NatElasticIp", {
      domain: "vpc",
      tags: [
        {
          key: "Name",
          value: `${props.resourceNamePrefix}-nat-eip`,
        },
      ],
    });

    this.natElasticIp.addResourceDependency(
      this.internetGatewayAttachment,
    );

    this.publicRouteTable = new ec2.CfnRouteTable(this, "PublicRouteTable", {
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
      gatewayId: this.internetGateway.ref,
      routeTableId: this.publicRouteTable.ref,
    });

    publicDefaultRoute.addResourceDependency(
      this.internetGatewayAttachment,
    );

    this.subnets = props.subnets.map((subnet) => {
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
          routeTableId: this.publicRouteTable.ref,
          subnetId: publicSubnet.ref,
        },
      );

      return publicSubnet;
    });

    this.natGateway = new ec2.CfnNatGateway(this, "NatGateway", {
      allocationId: this.natElasticIp.attrAllocationId,
      subnetId: this.subnets[0].ref,
      tags: [
        {
          key: "Name",
          value: `${props.resourceNamePrefix}-nat-gateway`,
        },
      ],
    });

    this.natGateway.addResourceDependency(
      this.internetGatewayAttachment,
    );
  }
}
