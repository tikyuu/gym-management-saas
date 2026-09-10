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
  }
}
