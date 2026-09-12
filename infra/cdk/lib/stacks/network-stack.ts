import { Stack, StackProps, Tags, aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";
import { ApplicationNetworkConstruct } from "../constructs/application-network-construct";
import { DatabaseNetworkConstruct } from "../constructs/database-network-construct";
import { PrivateIngressNetworkConstruct } from "../constructs/private-ingress-network-construct";
import { PublicNetworkConstruct } from "../constructs/public-network-construct";
import { SecurityGroupConstruct } from "../constructs/security-group-construct";
import type { SubnetConfig } from "../types/subnet-config";

interface NetworkStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
  vpcCidr: string;
  publicSubnets: SubnetConfig[];
  privateIngressSubnets: SubnetConfig[];
  applicationSubnets: SubnetConfig[];
  databaseSubnets: SubnetConfig[];
}

export class NetworkStack extends Stack {
  public readonly vpc: ec2.IVpc;

  constructor(scope: Construct, id: string, props: NetworkStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "network");

    this.vpc = new ec2.Vpc(this, "Vpc", {
      ipAddresses: ec2.IpAddresses.cidr(props.vpcCidr),
      natGateways: 0,
      subnetConfiguration: [],
      vpcName: `${resourceNamePrefix}-vpc`,
    });

    const securityGroups = new SecurityGroupConstruct(this, "SecurityGroups", {
      vpc: this.vpc,
      resourceNamePrefix,
    });

    const publicNetwork = new PublicNetworkConstruct(this, "PublicNetwork", {
      vpcId: this.vpc.vpcId,
      resourceNamePrefix,
      subnets: props.publicSubnets,
    });

    const privateIngressNetwork = new PrivateIngressNetworkConstruct(
      this,
      "PrivateIngressNetwork",
      {
        vpcId: this.vpc.vpcId,
        resourceNamePrefix,
        subnets: props.privateIngressSubnets,
      },
    );

    const applicationNetwork = new ApplicationNetworkConstruct(
      this,
      "ApplicationNetwork",
      {
        vpcId: this.vpc.vpcId,
        resourceNamePrefix,
        subnets: props.applicationSubnets,
        natGatewayId: publicNetwork.natGateway.ref,
      },
    );

    const databaseNetwork = new DatabaseNetworkConstruct(
      this,
      "DatabaseNetwork",
      {
        vpcId: this.vpc.vpcId,
        resourceNamePrefix,
        subnets: props.databaseSubnets,
      },
    );
  }
}
