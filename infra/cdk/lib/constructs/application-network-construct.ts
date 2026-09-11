import { Stack, aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";
import type { SubnetConfig } from "../types/subnet-config";

interface ApplicationNetworkConstructProps {
  vpcId: string;
  resourceNamePrefix: string;
  subnets: SubnetConfig[];
  natGatewayId: string;
}

export class ApplicationNetworkConstruct extends Construct {
  public readonly subnets: ec2.CfnSubnet[];

  constructor(
    scope: Construct,
    id: string,
    props: ApplicationNetworkConstructProps,
  ) {
    super(scope, id);

    const routeTable = new ec2.CfnRouteTable(this, "RouteTable", {
      tags: [
        {
          key: "Name",
          value: `${props.resourceNamePrefix}-private-application-rt`,
        },
      ],
      vpcId: props.vpcId,
    });

    new ec2.CfnRoute(this, "DefaultRoute", {
      destinationCidrBlock: "0.0.0.0/0",
      natGatewayId: props.natGatewayId,
      routeTableId: routeTable.ref,
    });

    new ec2.CfnVPCEndpoint(this, "S3GatewayEndpoint", {
      routeTableIds: [routeTable.ref],
      serviceName: `com.amazonaws.${Stack.of(this).region}.s3`,
      tags: [
        {
          key: "Name",
          value: `${props.resourceNamePrefix}-s3-gateway-endpoint`,
        },
      ],
      vpcEndpointType: "Gateway",
      vpcId: props.vpcId,
    });

    this.subnets = props.subnets.map((subnet) => {
      const applicationSubnet = new ec2.CfnSubnet(this, subnet.id, {
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
          routeTableId: routeTable.ref,
          subnetId: applicationSubnet.ref,
        },
      );

      return applicationSubnet;
    });
  }
}
