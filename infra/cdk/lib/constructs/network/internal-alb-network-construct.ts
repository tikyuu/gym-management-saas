import { aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";
import type { SubnetConfig } from "../../types/subnet-config";

interface InternalAlbNetworkConstructProps {
  vpcId: string;
  resourceNamePrefix: string;
  subnets: SubnetConfig[];
}

export class InternalAlbNetworkConstruct extends Construct {
  public readonly routeTable: ec2.CfnRouteTable;
  public readonly subnets: ec2.CfnSubnet[];

  constructor(
    scope: Construct,
    id: string,
    props: InternalAlbNetworkConstructProps,
  ) {
    super(scope, id);

    this.routeTable = new ec2.CfnRouteTable(this, "RouteTable", {
      tags: [
        {
          key: "Name",
          value: `${props.resourceNamePrefix}-private-ingress-rt`,
        },
      ],
      vpcId: props.vpcId,
    });

    this.subnets = props.subnets.map((subnet) => {
      const privateIngressSubnet = new ec2.CfnSubnet(this, subnet.id, {
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
          routeTableId: this.routeTable.ref,
          subnetId: privateIngressSubnet.ref,
        },
      );

      return privateIngressSubnet;
    });
  }
}
