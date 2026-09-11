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
  public readonly routeTable: ec2.CfnRouteTable;

  constructor(
    scope: Construct,
    id: string,
    props: ApplicationNetworkConstructProps,
  ) {
    super(scope, id);

    this.routeTable = new ec2.CfnRouteTable(this, "RouteTable", {
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
      routeTableId: this.routeTable.ref,
    });

    new ec2.CfnVPCEndpoint(this, "S3GatewayEndpoint", {
      routeTableIds: [this.routeTable.ref],
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
  }
}
