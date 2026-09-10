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
  }
}
