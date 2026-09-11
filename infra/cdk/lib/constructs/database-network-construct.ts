import { aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";
import type { SubnetConfig } from "../types/subnet-config";

interface DatabaseNetworkConstructProps {
  vpcId: string;
  resourceNamePrefix: string;
  subnets: SubnetConfig[];
}

export class DatabaseNetworkConstruct extends Construct {
  public readonly routeTable: ec2.CfnRouteTable;

  constructor(
    scope: Construct,
    id: string,
    props: DatabaseNetworkConstructProps,
  ) {
    super(scope, id);

    this.routeTable = new ec2.CfnRouteTable(this, "RouteTable", {
      tags: [
        {
          key: "Name",
          value: `${props.resourceNamePrefix}-private-database-rt`,
        },
      ],
      vpcId: props.vpcId,
    });
  }
}
