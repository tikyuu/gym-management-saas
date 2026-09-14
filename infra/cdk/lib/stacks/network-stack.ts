import { Stack, StackProps, Tags, aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";
import { ApplicationNetworkConstruct } from "../constructs/network/application-network-construct";
import { DatabaseNetworkConstruct } from "../constructs/network/database-network-construct";
import { InternalAlbNetworkConstruct } from "../constructs/network/internal-alb-network-construct";
import { PublicNetworkConstruct } from "../constructs/network/public-network-construct";
import { SecurityGroupConstruct } from "../constructs/network/security-group-construct";
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
  public readonly albSecurityGroup: ec2.ISecurityGroup;
  public readonly applicationSubnets: ec2.ISubnet[];
  public readonly databaseSubnetIds: string[];
  public readonly ecsSecurityGroup: ec2.ISecurityGroup;
  public readonly internalAlbSubnetIds: string[];
  public readonly rdsSecurityGroup: ec2.ISecurityGroup;
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

    this.albSecurityGroup = securityGroups.albSecurityGroup;
    this.ecsSecurityGroup = securityGroups.ecsSecurityGroup;
    this.rdsSecurityGroup = securityGroups.rdsSecurityGroup;

    const publicNetwork = new PublicNetworkConstruct(this, "PublicNetwork", {
      vpcId: this.vpc.vpcId,
      resourceNamePrefix,
      subnets: props.publicSubnets,
    });

    const internalAlbNetwork = new InternalAlbNetworkConstruct(
      this,
      "InternalAlbNetwork",
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

    this.applicationSubnets = applicationNetwork.subnets.map(
      (subnet, index) =>
        ec2.Subnet.fromSubnetAttributes(
          this,
          `ApplicationSubnetReference${index + 1}`,
          {
            availabilityZone: props.applicationSubnets[index].availabilityZone,
            routeTableId: applicationNetwork.routeTable.ref,
            subnetId: subnet.ref,
          },
        ),
    );
    this.internalAlbSubnetIds = internalAlbNetwork.subnets.map(
      (subnet) => subnet.ref,
    );
    this.databaseSubnetIds = databaseNetwork.subnets.map(
      (subnet) => subnet.ref,
    );
  }
}
