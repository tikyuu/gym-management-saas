import { aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";
import type { SubnetConfig } from "../types/subnet-config";

interface DatabaseNetworkConstructProps {
  vpcId: string;
  resourceNamePrefix: string;
  subnets: SubnetConfig[];
}

export class DatabaseNetworkConstruct extends Construct {
  public readonly subnets: ec2.CfnSubnet[];

  constructor(
    scope: Construct,
    id: string,
    props: DatabaseNetworkConstructProps,
  ) {
    super(scope, id);

    const routeTable = new ec2.CfnRouteTable(this, "RouteTable", {
      tags: [
        {
          key: "Name",
          value: `${props.resourceNamePrefix}-private-database-rt`,
        },
      ],
      vpcId: props.vpcId,
    });

    this.subnets = props.subnets.map((subnet) => {
      const databaseSubnet = new ec2.CfnSubnet(this, subnet.id, {
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
          subnetId: databaseSubnet.ref,
        },
      );

      return databaseSubnet;
    });
  }
}
